import os
import json
import datetime
import yt_dlp
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- Nossas Bibliotecas ---
from google.cloud import storage, firestore, tasks_v2
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from moviepy.editor import VideoFileClip, concatenate_videoclips

# --- Inicialização do App e Clientes ---
app = Flask(__name__)
CORS(app) # Habilita CORS para todas as rotas

# Configuração
# -----------------------------------------------------------------
# --- ⚠️ PREENCHA OS VALORES DO SEU NOVO PROJETO ABAIXO ⚠️ ---

MEU_PROJECT_ID = "video-editor-ia" # (O ID do seu novo projeto, ex: "video-editor-ia")
MINHA_LOCATION = "us-central1" 
MEU_BUCKET_GCS = "[ SUBSTITUA PELO NOME DO SEU NOVO BUCKET ]" # (ex: "meu-bucket-videos-novo")
MINHA_FILA_TASKS = "[ SUBSTITUA PELO NOME DA SUA NOVA FILA ]" # (ex: "minha-fila-de-corte")

# --- ✅ CONTAS DE SERVIÇO CORRIGIDAS (Baseado na sua imagem) ---

# Esta é a conta da API (editordevideo@...)
# Ela precisa do papel 'Criador de token da conta de serviço'.
API_SERVICE_ACCOUNT_EMAIL = "editordevideo@video-editor-ia.gserviceaccount.com"

# Esta é a conta do WORKER (editor-workerapi@...)
# Ela é usada no 'oidc_token' para o Cloud Tasks.
WORKER_SERVICE_ACCOUNT_EMAIL = "editor-workerapi@video-editor-ia.gserviceaccount.com" 

# --- ⚠️ PREENCHA COM A URL DO SEU WORKER ⚠️ ---
# (Esta é a URL do seu serviço 'novoprojeto')
SERVICE_URL = "https://novoprojeto-709237674340.us-central1.run.app" # (Verifique se esta é a URL correta do seu 'novoprojeto')
# -----------------------------------------------------------------


# Inicializa os clientes (Globais)
# Nota: O código original usava database="edify". Mantenha isso se você criou o Firestore com esse ID.
db = firestore.Client(project=MEU_PROJECT_ID, database="edify") 
tasks_client = tasks_v2.CloudTasksClient()
storage_client = storage.Client(project=MEU_PROJECT_ID)
tasks_queue_path = tasks_client.queue_path(MEU_PROJECT_ID, MINHA_LOCATION, MINHA_FILA_TASKS)
BUCKET = storage_client.bucket(MEU_BUCKET_GCS)
vertexai.init(project=MEU_PROJECT_ID, location=MINHA_LOCATION)
AI_MODEL = GenerativeModel("gemini-2.5-flash") # Usando 1.5-flash para garantir


# #######################################################################
# --- FUNÇÕES CORE (Helper Functions) ---
# #######################################################################

def analisa_video_com_ia(gcs_uri, prompt):
    """ Chama a IA para analisar o vídeo e retornar uma lista JSON de timestamps. """
    print(f"Chamando Gemini para analisar: {gcs_uri} com prompt: {prompt}")
    
    video_part = Part.from_uri(uri=gcs_uri, mime_type="video/mp4") 
    prompt_completo = f"""
    Analise este vídeo quadro a quadro com o seguinte objetivo: "{prompt}".
    Sua tarefa é identificar todos os segmentos de tempo (o mais preciso possível) 
    em que o conteúdo solicitado é visível.
    Responda SOMENTE com uma lista JSON no formato:
    [
      {{ "inicio_segundos": 4.5, "fim_segundos": 8.0 }},
      {{ "inicio_segundos": 12.0, "fim_segundos": 15.2 }}
    ]
    Se nada for encontrado, retorne uma lista JSON vazia: [].
    """
    
    contents = [video_part, prompt_completo]
    response = AI_MODEL.generate_content(contents, stream=False)
    
    try:
        raw_text = response.candidates[0].content.parts[0].text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        timestamps = json.loads(raw_text)
        print(f"IA retornou {len(timestamps)} segmentos de corte.")
        return timestamps
        
    except (json.JSONDecodeError, IndexError, AttributeError) as e:
        print(f"ERRO: Falha ao parsear JSON da IA. Resposta bruta: {response.text[:200]}... Erro: {e}")
        raise ValueError(f"A IA não retornou um formato JSON válido. Resposta: {response.text[:200]}")


def corta_e_junta_video(gcs_uri_original, gcs_uri_final, timestamps):
    """ Baixa, corta, junta os clipes e faz upload do vídeo final. """
    print(f"Iniciando corte para: {gcs_uri_original}")
    # Extrai o nome do arquivo para usar no /tmp
    nome_original = gcs_uri_original.split('/')[-1]
    nome_final = gcs_uri_final.split('/')[-1]
    
    arquivo_local_original = f"/tmp/{nome_original}"
    arquivo_local_final = f"/tmp/{nome_final}"
    os.makedirs(os.path.dirname(arquivo_local_original), exist_ok=True)

    try:
        # 1. Baixa o vídeo original
        blob_original = BUCKET.blob(gcs_uri_original.replace(f"gs://{MEU_BUCKET_GCS}/", ""))
        blob_original.download_to_filename(arquivo_local_original)
        
        # 2. Inicia processo de corte
        video_principal = VideoFileClip(arquivo_local_original)
        clips_finais = []
        
        # Correção do Bug do JSON: Lê uma lista de dicionários
        for segmento in timestamps:
            inicio = segmento['inicio_segundos']
            fim = segmento['fim_segundos']

            if fim > video_principal.duration: fim = video_principal.duration
            if inicio > video_principal.duration: continue
            if inicio < 0: inicio = 0
            
            clips_finais.append(video_principal.subclip(inicio, fim))
            
        if not clips_finais: 
            print("Nenhum clipe válido encontrado após a filtragem.")
            return None

        # 3. Junta os clipes e escreve
        video_concatenado = concatenate_videoclips(clips_finais)
        # codec e audio_codec são importantes para compatibilidade web
        video_concatenado.write_videofile(arquivo_local_final, codec="libx264", audio_codec="aac")
        
        video_principal.close(); video_concatenado.close()

        # 4. Faz upload do arquivo final
        blob_final = BUCKET.blob(gcs_uri_final.replace(f"gs://{MEU_BUCKET_GCS}/", ""))
        blob_final.upload_from_filename(arquivo_local_final)
        
        # 5. Torna público
        blob_final.make_public()
        print(f"Arquivo final tornado público: {blob_final.public_url}")
        
        return blob_final.public_url
        
    finally:
        # Limpeza
        if os.path.exists(arquivo_local_original): os.remove(arquivo_local_original)
        if os.path.exists(arquivo_local_final): os.remove(arquivo_local_final)


def baixa_video_url(video_url, gcs_uri_destino):
    """ Baixa um vídeo de uma URL (YouTube, etc.) e faz upload para o GCS. """
    print(f"Iniciando download de {video_url}")
    nome_destino = gcs_uri_destino.split('/')[-1]
    arquivo_local_download = f"/tmp/{nome_destino}"
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': arquivo_local_download,
        'quiet': True, 'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            print("Download concluído com sucesso.")

        # Faz upload para o GCS
        blob_destino = BUCKET.blob(gcs_uri_destino.replace(f"gs://{MEU_BUCKET_GCS}/", ""))
        blob_destino.upload_from_filename(arquivo_local_download)
        
        return True
        
    except yt_dlp.utils.DownloadError as e:
        print(f"ERRO: Falha no download com yt-dlp: {e}")
        raise ValueError("Não foi possível baixar o vídeo da URL fornecida.")
    finally:
        if os.path.exists(arquivo_local_download): os.remove(arquivo_local_download)


# #######################################################################
# --- ROTAS DA API (Endpoints) ---
# #######################################################################

@app.route('/gerar-url-upload', methods=['POST'])
def gerar_url_upload():
    """ 1. Retorna uma URL assinada para upload direto para o GCS. """
    data = request.json
    filename = data.get('filename')
    content_type = data.get('content_type')
    
    if not filename or not content_type: return jsonify({"error": "Parâmetros ausentes."}), 400

    try:
        gcs_uri = f"uploads/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        blob = BUCKET.blob(gcs_uri)
        
        # --- ✅ CORREÇÃO (Erro 500 / "no private key") ---
        # Força a biblioteca a usar a API IAM (signBlob) para assinar,
        # usando o e-mail da conta de serviço DESTA API.
        upload_url = blob.generate_signed_url(
            version="v4", 
            expiration=datetime.timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
            service_account_email=API_SERVICE_ACCOUNT_EMAIL 
        )
        # --- FIM DA CORREÇÃO ---
        
        return jsonify({"upload_url": upload_url, "gcs_uri": f"gs://{MEU_BUCKET_GCS}/{gcs_uri}"})

    except Exception as e:
        print(f"Erro ao gerar URL assinada: {e}")
        return jsonify({"error": f"Falha ao gerar URL: {str(e)}"}), 500


@app.route('/iniciar-job', methods=['POST'])
def iniciar_job_upload():
    """ 2. Recebe o GCS URI do vídeo recém-carregado e cria um Job no Firestore. """
    data = request.json
    gcs_uri = data.get('gcs_uri'); prompt = data.get('prompt')
    if not gcs_uri or not prompt: return jsonify({"error": "Parâmetros ausentes."}), 400

    try:
        job_ref = db.collection('jobs').document()
        job_data = {
            'id': job_ref.id, 'status': 'PENDENTE', 'prompt': prompt, 'gcs_uri_original': gcs_uri,
            'criado_em': firestore.SERVER_TIMESTAMP, 'tipo': 'UPLOAD',
        }
        job_ref.set(job_data)
        
        payload = json.dumps({'job_id': job_ref.id, 'tipo': 'UPLOAD'})
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST, 'url': f'{SERVICE_URL}/processar-job',
                'headers': {'Content-type': 'application/json'}, 'body': payload.encode(),
                
                # --- ✅ CORREÇÃO: Usa a conta do WORKER para o token OIDC ---
                'oidc_token': {
                    'service_account_email': WORKER_SERVICE_ACCOUNT_EMAIL
                }
                # --- FIM DA CORREÇÃO ---
            }
        }
        tasks_client.create_task(parent=tasks_queue_path, task=task)
        return jsonify({"job_id": job_ref.id, "status": "processamento_iniciado"})

    except Exception as e:
        print(f"Erro ao iniciar job: {e}")
        return jsonify({"error": "Falha ao criar o job de processamento."}), 500


@app.route('/iniciar-job-por-url', methods=['POST'])
def iniciar_job_url():
    """ 3. Recebe uma URL de vídeo e cria um Job com status 'PENDENTE_URL'. """
    data = request.json
    video_url = data.get('video_url'); prompt = data.get('prompt')
    if not video_url or not prompt: return jsonify({"error": "Parâmetros ausentes."}), 400

    try:
        job_ref = db.collection('jobs').document()
        job_data = {
            'id': job_ref.id, 'status': 'PENDENTE_URL', 'prompt': prompt, 'url_original': video_url,
            'criado_em': firestore.SERVER_TIMESTAMP, 'tipo': 'URL',
        }
        job_ref.set(job_data)
        
        payload = json.dumps({'job_id': job_ref.id, 'tipo': 'URL'})
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST, 'url': f'{SERVICE_URL}/processar-job-url',
                'headers': {'Content-type': 'application/json'}, 'body': payload.encode(),
                
                # --- ✅ CORREÇÃO: Usa a conta do WORKER para o token OIDC ---
                'oidc_token': {
                    'service_account_email': WORKER_SERVICE_ACCOUNT_EMAIL
                }
                # --- FIM DA CORREÇÃO ---
            }
        }
        tasks_client.create_task(parent=tasks_queue_path, task=task)
        
        return jsonify({"job_id": job_ref.id, "status": "processamento_iniciado"})

    except Exception as e:
        print(f"Erro ao iniciar job de URL: {e}")
        return jsonify({"error": "Falha ao criar o job de URL."}), 500


@app.route('/verificar-job/<jobId>', methods=['GET'])
def verificar_job(jobId):
    """ 4. Rota de Polling para o front-end verificar o status de um Job. """
    try:
        job_doc = db.collection('jobs').document(jobId).get()
        if job_doc.exists:
            return jsonify(job_doc.to_dict())
        else:
            return jsonify({"error": "Job não encontrado."}), 404
    except Exception as e:
        print(f"Erro ao verificar job: {e}")
        return jsonify({"error": "Falha ao acessar o status do job."}), 500


@app.route('/processar-job-url', methods=['POST'])
def worker_processar_job_url():
    """ 5. WORKER: Rota acionada para Jobs de URL (etapa de DOWNLOAD). """
    job_ref = None # Define job_ref como None para o bloco 'except'
    try:
        data = request.json
        job_id = data.get('job_id')
        job_ref = db.collection('jobs').document(job_id)
        job_data = job_ref.get().to_dict()

        if not job_data or job_data.get('status') != 'PENDENTE_URL': 
            print(f"Job {job_id} não encontrado ou status inválido. Ignorando.")
            return 'OK', 200

        video_url = job_data.get('url_original')
        gcs_uri_destino = f"uploads/{job_id}_{video_url.split('/')[-1]}.mp4"
        
        job_ref.update({'status': 'BAIXANDO', 'gcs_uri_original': f"gs://{MEU_BUCKET_GCS}/{gcs_uri_destino}"})

        # Baixa e faz upload
        baixa_video_url(video_url, gcs_uri_destino) 
        
        # Cria a tarefa para o próximo worker (Corte e IA)
        job_ref.update({'status': 'PENDENTE'}) 
        payload = json.dumps({'job_id': job_id, 'tipo': 'UPLOAD'}) 
        task = {
            'http_request': {'http_method': tasks_v2.HttpMethod.POST, 'url': f'{SERVICE_URL}/processar-job',
                'headers': {'Content-type': 'application/json'}, 'body': payload.encode(),
                
                # --- ✅ CORREÇÃO: Usa a conta do WORKER para o token OIDC ---
                'oidc_token': {
                    'service_account_email': WORKER_SERVICE_ACCOUNT_EMAIL
                }
                # --- FIM DA CORREÇÃO ---
            }
        }
        tasks_client.create_task(parent=tasks_queue_path, task=task)
        
        return 'OK', 200

    except Exception as e:
        print(f"ERRO no Worker (URL): {e}")
        if job_ref:
            job_ref.update({'status': 'ERRO', 'erro_info': f"[Worker URL]: {str(e)}"})
        return 'OK', 200 # Retorna 200 para o Cloud Tasks não tentar novamente


@app.route('/processar-job', methods=['POST'])
def worker_processar_job():
    """ 6. WORKER: Rota acionada para Jobs de UPLOAD e a segunda etapa dos Jobs de URL. """
    job_ref = None # Define job_ref como None para o bloco 'except'
    try:
        data = request.json
        job_id = data.get('job_id')
        job_ref = db.collection('jobs').document(job_id)
        job_data = job_ref.get().to_dict()

        if not job_data or job_data.get('status') != 'PENDENTE': 
            print(f"Job {job_id} não encontrado ou status inválido. Ignorando.")
            return 'OK', 200

        gcs_uri = job_data.get('gcs_uri_original'); prompt = job_data.get('prompt')
        
        job_ref.update({'status': 'PROCESSANDO'})
        
        # 1. Análise de vídeo com IA (Gemini)
        timestamps = analisa_video_com_ia(gcs_uri, prompt)
        
        # 2. Define o nome do arquivo final
        gcs_uri_base = gcs_uri.split('/')[-1]
        gcs_uri_final = f"edicoes/editado_{gcs_uri_base}"
        
        # 3. Corte e Upload do vídeo editado
        # Passa o nome do blob (sem o prefixo) para a função de corte
        public_url = corta_e_junta_video(gcs_uri.replace(f"gs://{MEU_BUCKET_GCS}/", ""), 
                                        gcs_uri_final, 
                                        timestamps)
        
        # 4. Atualiza o Firestore
        if public_url:
            job_ref.update({'status': 'CONCLUÍDO', 'url_video_final': public_url})
        else:
            erro_msg = "A IA não encontrou segmentos de vídeo correspondentes ao seu prompt."
            job_ref.update({'status': 'ERRO', 'erro_info': erro_msg})

        return 'OK', 200

    except Exception as e:
        print(f"ERRO no Worker (Processar): {e}")
        if job_ref:
            job_ref.update({'status': 'ERRO', 'erro_info': f"[Worker Processar]: {str(e)}"})
        return 'OK', 200 # Retorna 200 para o Cloud Tasks não tentar novamente

# --- Ponto de Entrada ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)
