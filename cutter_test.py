# Importa as classes necessárias do MoviePy
from moviepy.editor import VideoFileClip, concatenate_videoclips
import os

def cortar_e_juntar_video(arquivo_original, arquivo_saida, timestamps):
    """
    Corta um vídeo com base em uma lista de timestamps (inicio, fim) e 
    junta os clipes resultantes em um novo arquivo.
    """
    
    # Lista para armazenar os clipes que vamos cortar
    clips_finais = []

    print(f"Iniciando o processo para o arquivo: {arquivo_original}")

    try:
        # 1. Carrega o vídeo original
        video_principal = VideoFileClip(arquivo_original)
        
        # 2. Itera sobre a lista de timestamps
        for i, (inicio, fim) in enumerate(timestamps):
            print(f"Cortando segmento {i+1}: de {inicio}s até {fim}s")
            
            # 3. Cria o sub-clipe com o tempo de início e fim
            #    Verifica se o fim não ultrapassa a duração do vídeo
            if fim > video_principal.duration:
                print(f"Aviso: O tempo final {fim}s ultrapassa a duração do vídeo ({video_principal.duration}s). Ajustando para o final.")
                fim = video_principal.duration
            
            if inicio > video_principal.duration:
                 print(f"Aviso: O tempo inicial {inicio}s está além do final do vídeo. Pulando este clipe.")
                 continue

            novo_clipe = video_principal.subclip(inicio, fim)
            clips_finais.append(novo_clipe)

        # 4. Verifica se temos clipes para juntar
        if not clips_finais:
            print("Nenhum clipe foi extraído. Nenhum arquivo de saída será criado.")
            video_principal.close()
            return

        # 5. Junta todos os clipes da lista em um único clipe
        print("Juntando os clipes...")
        video_concatenado = concatenate_videoclips(clips_finais)

        # 6. Escreve o resultado no arquivo de saída
        #    codec="libx264" é recomendado para compatibilidade (arquivos .mp4)
        video_concatenado.write_videofile(arquivo_saida, codec="libx264", audio_codec="aac")

        print(f"\nSucesso! 🚀 Vídeo salvo em: {arquivo_saida}")

    except Exception as e:
        print(f"\nOcorreu um erro: {e}")
        print("---")
        print("Possíveis causas:")
        print("1. O FFmpeg não está instalado ou não foi encontrado (verifique o 'PATH' do sistema).")
        print(f"2. O arquivo '{arquivo_original}' não foi encontrado.")
        print("3. Ocorreu um erro ao ler ou escrever o arquivo de vídeo.")
    
    finally:
        # 7. Fecha os clipes para liberar os arquivos
        if 'video_principal' in locals():
            video_principal.close()
        for clipe in clips_finais:
            clipe.close()

# --- CONFIGURAÇÃO DO TESTE ---

# 1. Coloque o nome do seu vídeo de teste aqui
#    (O arquivo deve estar na mesma pasta do script)
VIDEO_ENTRADA = "video1.mp4" 

# 2. Defina os cortes que você quer fazer (em segundos)
#    Formato: [ (inicio_1, fim_1), (inicio_2, fim_2), ... ]
LISTA_DE_CORTES = [
    (5, 10),      # Pega dos 5 segundos até os 10 segundos
    (25, 30),     # Pega dos 25 segundos até os 30 segundos
    (62, 65)      # Pega dos 62 segundos até os 65 segundos
]

# 3. Defina o nome do arquivo final
VIDEO_SAIDA = "video_cortado.mp4"

# --- EXECUÇÃO ---

if __name__ == "__main__":
    if not os.path.exists(VIDEO_ENTRADA):
        print(f"Erro: Arquivo de entrada '{VIDEO_ENTRADA}' não encontrado.")
        print("Por favor, coloque seu vídeo de teste na mesma pasta e renomeie a variável 'VIDEO_ENTRADA'.")
    else:
        cortar_e_juntar_video(VIDEO_ENTRADA, VIDEO_SAIDA, LISTA_DE_CORTES)