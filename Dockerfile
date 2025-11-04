# 1. Use a imagem base oficial do Python
FROM python:3.11-slim

# 2. Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Instale o FFmpeg (essencial para o MoviePy)
#    - apt-get update: Atualiza a lista de pacotes
#    - -y: Diz "sim" para todas as perguntas
#    - ffmpeg: O programa que queremos
#    - rm -rf ...: Limpa o cache para manter a imagem pequena
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 4. Copie o arquivo de requisitos
COPY requirements.txt .

# 5. Instale as bibliotecas Python
#    Usamos a versão específica do moviepy que funcionou!
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copie todo o resto do seu código (app.py, etc)
COPY . .

# 7. Comando para iniciar o servidor (Gunicorn é o padrão para produção)
#    Ele escuta na porta 8080, que o Cloud Run espera.
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]