import vertexai
from vertexai.generative_models import GenerativeModel, Part

def analisar_video_com_ia(project_id, location, gcs_uri, prompt):
    """
    Analisa um vídeo no Google Cloud Storage usando um modelo multimodal 
    do Vertex AI (Gemini) e retorna a resposta de texto.
    """
    
    print(f"Iniciando Vertex AI para o projeto {project_id} em {location}...")
    try:
        # 1. Inicializa o Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # 2. Carrega o modelo (Gemini 1.0 Pro Vision)
        # Usamos 'gemini-1.0-pro-vision' para análise de vídeo
        model = GenerativeModel("gemini-2.5-flash")

        print(f"Carregando vídeo de: {gcs_uri}")
        
        # 3. Prepara o input do vídeo
        # A API lê o vídeo diretamente do GCS.
        video_part = Part.from_uri(
            uri=gcs_uri,
            mime_type="video/mp4" # Informa à API que é um vídeo MP4
        )

        # 4. Prepara o conteúdo da requisição (Vídeo + Prompt)
        contents = [video_part, prompt]

        print("Enviando solicitação para a IA (isso pode levar alguns minutos)...")
        
        # 5. Chama a IA
        # O 'stream=False' significa que esperamos a resposta completa
        response = model.generate_content(contents, stream=False)
        
        # 6. Extrai e imprime a resposta de texto
        if response.candidates:
            resposta_texto = response.candidates[0].content.parts[0].text
            print("\n--- Resposta da IA ---")
            print(resposta_texto)
            print("------------------------")
            return resposta_texto
        else:
            print("\nA IA não retornou uma resposta válida.")
            return None

    except Exception as e:
        print(f"\nOcorreu um erro ao chamar a API do Vertex AI: {e}")
        print("---")
        print("Possíveis causas:")
        print("1. A API 'Vertex AI' não está ativada no seu projeto Google Cloud.")
        print("2. O 'PROJECT_ID' ou 'LOCATION' estão incorretos.")
        print(f"3. O bucket ou arquivo '{gcs_uri}' não existe ou a IA não tem permissão para lê-lo.")
        print("4. Sua autenticação local falhou (tente rodar 'gcloud auth application-default login' novamente).")

# --- CONFIGURAÇÃO DO TESTE ---

# 1. Substitua pelo ID do seu projeto no Google Cloud
MEU_PROJECT_ID = "strategic-haven-468504-u5" 

# 2. Substitua pela localização do seu projeto (ex: "us-central1")
MINHA_LOCATION = "us-central1"

# 3. Substitua pelo caminho (URI) do seu vídeo no Google Cloud Storage
MEU_GCS_URI = "gs://bucket-editor-ia-12345/video1.mp4" 

# 4. Este é o prompt. Estamos pedindo um JSON.
#    Altere 'uma pessoa' para o que você quiser encontrar no seu vídeo.
MEU_PROMPT = """
Analise este vídeo quadro a quadro.
Sua tarefa é identificar todos os segmentos de tempo em que 'um passaro' aparece visivelmente.

Responda SOMENTE com uma lista JSON.
Cada item na lista deve ser um objeto com duas chaves: "inicio_segundos" e "fim_segundos".
Os tempos devem ser números (inteiros ou flutuantes).

Exemplo de resposta:
[
  { "inicio_segundos": 4.5, "fim_segundos": 8.0 },
  { "inicio_segundos": 12.0, "fim_segundos": 15.2 }
]

Se nada for encontrado, retorne uma lista JSON vazia: [].
"""

# --- EXECUÇÃO ---

if __name__ == "__main__":
    # CORREÇÃO: A verificação de segurança foi removida para executar o script diretamente.
    analisar_video_com_ia(MEU_PROJECT_ID, MINHA_LOCATION, MEU_GCS_URI, MEU_PROMPT)