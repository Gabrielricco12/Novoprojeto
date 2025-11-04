import os
import json # Usado para "ler" a resposta da IA
from google.cloud import storage # Nova biblioteca para upload

# --- Importações da Fase 2 (IA) ---
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# --- Importações da Fase 1 (Corte) ---
from moviepy.editor import VideoFileClip, concatenate_videoclips

# 
# --- FUNÇÃO 1: UPLOAD (Sem alterações) ---
#
def upload_para_gcs(bucket_name, arquivo_local, nome_destino_blob):
    """Faz o upload de um arquivo local para o Google Cloud Storage."""
    print(f"Iniciando upload de '{arquivo_local}' para gs://{bucket_name}/{nome_destino_blob}...")
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(nome_destino_blob)

        blob.upload_from_filename(arquivo_local)

        print("Upload concluído.")
        # Retorna o URI completo do GCS que a IA precisa
        return f"gs://{bucket_name}/{nome_destino_blob}"
    except Exception as e:
        print(f"Erro no upload para GCS: {e}")
        print("Verifique se o nome do bucket está correto e se sua autenticação 'gcloud' está ativa.")
        return None

# 
# --- FUNÇÃO 2: ANÁLISE DE IA (Sem alterações) ---
#
def analisar_video_com_ia(project_id, location, gcs_uri, prompt):
    """Analisa o vídeo no GCS e retorna a resposta JSON da IA."""
    print(f"Iniciando Vertex AI (Projeto: {project_id})...")
    try:
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel("gemini-2.5-flash")

        print(f"Carregando vídeo de: {gcs_uri}")
        video_part = Part.from_uri(uri=gcs_uri, mime_type="video/mp4")
        contents = [video_part, prompt]

        print("Enviando solicitação para a IA (pode levar alguns minutos)...")
        response = model.generate_content(contents, stream=False)
        
        if response.candidates:
            resposta_texto = response.candidates[0].content.parts[0].text
            print("IA respondeu com sucesso.")
            return resposta_texto
        else:
            print("A IA não retornou uma resposta válida.")
            return None
    except Exception as e:
        print(f"Erro ao chamar a API do Vertex AI: {e}")
        return None

# 
# --- FUNÇÃO 3: PARSE DO JSON (!!! CÓDIGO CORRIGIDO E ROBUSTO !!!) ---
#
def parsear_resposta_json(resposta_texto):
    """
    Converte a resposta em texto da IA em uma lista de tuplas.
    Esta versão é robusta e extrai o JSON mesmo que a IA adicione
    texto extra (como ```json ou outras notas).
    """
    print("Analisando resposta JSON da IA...")
    json_limpo = "" # Variável para guardar o JSON que tentamos decodificar
    
    try:
        # 1. Encontra o início da lista JSON (o primeiro '[')
        inicio_json = resposta_texto.find('[')
        
        # 2. Encontra o fim da lista JSON (o último ']')
        #    rfind() procura de trás para frente, garantindo que pegamos o fim correto
        fim_json = resposta_texto.rfind(']')
        
        # 3. Verifica se encontramos um início e um fim
        if inicio_json == -1 or fim_json == -1:
            print("Erro: Não foi possível encontrar o início '[' ou o fim ']' da lista JSON na resposta.")
            print(f"Resposta recebida: {resposta_texto}")
            return []
            
        # 4. Extrai o texto JSON limpo (tudo entre o primeiro '[' e o último ']')
        json_limpo = resposta_texto[inicio_json : fim_json + 1]
        
        # 5. Converte o texto JSON em uma estrutura de dados Python
        dados = json.loads(json_limpo)
        
        # 6. Converte a lista de dicionários no formato que o MoviePy precisa
        timestamps = []
        for item in dados:
            # Adiciona uma verificação de segurança para o caso do JSON estar malformado
            if 'inicio_segundos' in item and 'fim_segundos' in item:
                inicio = item['inicio_segundos']
                fim = item['fim_segundos']
                timestamps.append((inicio, fim))
            
        print(f"Timestamps extraídos: {len(timestamps)} segmentos encontrados.")
        return timestamps

    except Exception as e:
        print(f"Erro ao decodificar o JSON da IA: {e}")
        print(f"Texto que falhou no parse: {json_limpo}")
        print(f"Resposta original completa: {resposta_texto}")
        return []

# 
# --- FUNÇÃO 4: CORTE DE VÍDEO (Sem alterações) ---
#
def cortar_e_juntar_video(arquivo_original, arquivo_saida, timestamps):
    """Corta o vídeo local com base nos timestamps e salva o resultado."""
    print(f"Iniciando processo de corte para: {arquivo_original}")
    clips_finais = []
    
    try:
        video_principal = VideoFileClip(arquivo_original)
        
        for i, (inicio, fim) in enumerate(timestamps):
            print(f"Cortando segmento {i+1}: de {inicio}s até {fim}s")
            
            if fim > video_principal.duration:
                fim = video_principal.duration
            if inicio > video_principal.duration:
                continue

            novo_clipe = video_principal.subclip(inicio, fim)
            clips_finais.append(novo_clipe)

        if not clips_finais:
            print("Nenhum clipe válido para extrair.")
            video_principal.close()
            return False

        print("Juntando os clipes...")
        video_concatenado = concatenate_videoclips(clips_finais)
        
        video_concatenado.write_videofile(arquivo_saida, codec="libx264", audio_codec="aac")

        print(f"\nSucesso! 🚀 Vídeo final salvo em: {arquivo_saida}")
        return True

    except Exception as e:
        print(f"\nOcorreu um erro no MoviePy/FFmpeg: {e}")
        return False
    
    finally:
        if 'video_principal' in locals():
            video_principal.close()
        for clipe in clips_finais:
            clipe.close()

# --- CONFIGURAÇÃO PRINCIPAL ---

# 1. Google Cloud
MEU_PROJECT_ID = "strategic-haven-468504-u5"
MINHA_LOCATION = "us-central1"
MEU_BUCKET_GCS = "bucket-editor-ia-12345" # Apenas o nome do bucket

# 2. Arquivos de Vídeo
VIDEO_LOCAL_ENTRADA = "video1.mp4"       # Seu vídeo local
VIDEO_FINAL_SAIDA = "resultado_final.mp4" # O nome do arquivo cortado

# 3. IA Prompt (!!! PROMPT CORRIGIDO E MAIS RIGOROSO !!!)
MEU_PROMPT = """
Sua tarefa é encontrar segmentos de tempo específicos em um vídeo onde 'um passaro' está visível.

Analise o vídeo.

Responda APENAS com uma lista JSON.
- Se você encontrar o objeto, retorne uma lista de objetos:
[
  { "inicio_segundos": 9.5, "fim_segundos": 12.0 }
]
- Se você NÃO encontrar o objeto 'um passaro' em NENHUM momento, retorne uma lista JSON vazia:
[]

NÃO adicione nenhuma outra palavra, explicação ou nota fora da lista JSON.
Sua resposta inteira deve ser APENAS o JSON.
"""

# --- EXECUÇÃO MESTRA ---

if __name__ == "__main__":
    print("--- INICIANDO PROCESSO COMPLETO (FASE 3) ---")

    # ETAPA 1: Upload do vídeo local para o GCS
    gcs_uri = upload_para_gcs(MEU_BUCKET_GCS, VIDEO_LOCAL_ENTRADA, "video_para_analise.mp4")
    
    if gcs_uri:
        # ETAPA 2: Análise do vídeo pela IA
        resposta_json_texto = analisar_video_com_ia(MEU_PROJECT_ID, MINHA_LOCATION, gcs_uri, MEU_PROMPT)
        
        if resposta_json_texto:
            # ETAPA 3: Parse da resposta da IA
            lista_de_cortes = parsear_resposta_json(resposta_json_texto)
            
            if lista_de_cortes:
                # ETAPA 4: Corte do vídeo local
                cortar_e_juntar_video(VIDEO_LOCAL_ENTRADA, VIDEO_FINAL_SAIDA, lista_de_cortes)
            else:
                print("A IA não encontrou segmentos para cortar (lista vazia).")
        else:
            print("A IA falhou em analisar o vídeo.")
    else:
        print("O upload para o GCS falhou. O processo foi interrompido.")

    print("--- PROCESSO FINALIZADO ---")