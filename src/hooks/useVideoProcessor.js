import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

// =======================================================
// --- 1. DEFINIÇÃO DOS TIPOS (APENAS COMENTÁRIO) ---
// Note que as interfaces TypeScript foram removidas.
// =======================================================

// --- CONFIGURAÇÃO ---
// --- ✅ CORREÇÃO APLICADA ABAIXO ---
// (Substitua pela URL do seu NOVO serviço 'editar-video-api' do projeto 'video-editor-ia')
const API_BASE_URL = "https://editar-video-api-709237674340.us-central1.run.app";
// Ex: "https://editar-video-api-xxxxxxxx-uc.a.run.app"
// --------------------

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// =======================================================
// --- 2. SERVIÇO DE API (SEM SINTAXE DE TIPO) ---
// =======================================================

const InternalApiService = {
  // Funções de API sem tipos (usando a URL interna)
  generateUploadUrl: async (params) => {
    const response = await apiClient.post('/gerar-url-upload', params);
    return response.data;
  },
  startUploadJob: async (params) => {
    const response = await apiClient.post('/iniciar-job', params);
    return response.data;
  },
  startUrlJob: async (params) => {
    const response = await apiClient.post('/iniciar-job-por-url', params);
    return response.data;
  },
  getJobStatus: async (jobId) => {
    const response = await apiClient.get(`/verificar-job/${jobId}`);
    return response.data;
  },
  uploadFileToGCS: async (uploadUrl, file, onProgress) => {
    await axios.put(uploadUrl, file, {
      headers: { 'Content-Type': file.type },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
        }
      },
    });
  },
};


// =======================================================
// --- 3. LÓGICA DO HOOK (useVideoProcessor) ---
// =======================================================

const HISTORY_STORAGE_KEY = 'videoEditorHistory';

// Hook interno para ler/salvar o histórico (agora sem tipos)
function useJobHistory() {
  const [history, setHistory] = useState(() => {
    try {
      const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      console.error("Falha ao ler o histórico do localStorage", e);
      return [];
    }
  });

  const updateHistory = (item) => {
    setHistory((prev) => {
      const existingIndex = prev.findIndex((h) => h.jobId === item.jobId);
      let newHistory = [...prev];
      if (existingIndex > -1) {
        newHistory[existingIndex] = item;
      } else {
        newHistory.unshift(item);
      }
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(newHistory));
      return newHistory;
    });
  };

  return { history, updateHistory };
}

// O hook principal (exportado)
export function useVideoProcessor() {
  const [jobId, setJobId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('Pronto para começar.');
  const [progress, setProgress] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState(null);
  const { history, updateHistory } = useJobHistory();

  // --- Monitoramento (Polling) ---
  const { data: jobData } = useQuery({
    queryKey: ['jobStatus', jobId],
    queryFn: () => {
      if (!jobId) throw new Error('Job ID inválido');
      return InternalApiService.getJobStatus(jobId);
    },
    enabled: !!jobId,
    refetchOnWindowFocus: false,
    refetchInterval: (query) => {
      const data = query.state.data;
      const status = data?.status;
      if (status === 'CONCLUÍDO' || status === 'ERRO') {
        return false;
      }
      return 5000;
    },
  });

  // --- Efeito para reagir a mudanças do Polling ---
  useEffect(() => {
    if (!jobData) return;

    const statusMap = {
      PENDENTE: 'Na fila... Aguardando processamento.',
      PENDENTE_URL: 'Na fila... Aguardando download.',
      BAIXANDO: 'Baixando vídeo do link...',
      PROCESSANDO: 'Processando na nuvem... (IA e corte)',
      CONCLUÍDO: 'Processo Concluído!',
      ERRO: 'Ocorreu um erro no processamento.',
    };
    setStatus(statusMap[jobData.status] || jobData.status);

    const finishJob = (jobStatus, resultUrl, errorMessage) => {
      setIsLoading(false);
      setJobId(null); 

      const historyItem = history.find((h) => h.jobId === jobData.id);
      if (historyItem) {
        updateHistory({
          ...historyItem, status: jobStatus, resultUrl: resultUrl, error: errorMessage,
        });
      }
    };

    if (jobData.status === 'CONCLUÍDO') {
      setDownloadUrl(jobData.url_video_final || null);
      finishJob('Completo', jobData.url_video_final);
    }
    if (jobData.status === 'ERRO') {
      setError(jobData.erro_info || 'Ocorreu um erro desconhecido.');
      finishJob('Falhou', undefined, jobData.erro_info);
    }
  }, [jobData, history, updateHistory]);

  const startJob = (jobId, prompt, fileNameOrUrl) => {
    updateHistory({ jobId, prompt, fileNameOrUrl, status: 'PENDENTE' });
    setJobId(jobId);
  };

  const submitFileJob = useCallback(
    async (file, prompt) => {
      setIsLoading(true);
      setError(null); setProgress(0); setDownloadUrl(null); setJobId(null);
      try {
        setStatus('1/4: Solicitando URL de upload...');
        const { upload_url, gcs_uri } = await InternalApiService.generateUploadUrl({
          filename: file.name, content_type: file.type,
        });
        setStatus('2/4: Fazendo upload do vídeo...');
        await InternalApiService.uploadFileToGCS(upload_url, file, (p) => setProgress(p));
        setStatus('3.5/4: Iniciando processamento...'); // Corrigido
        const { job_id } = await InternalApiService.startUploadJob({ gcs_uri, prompt });
        setStatus('4/4: Aguardando na fila da nuvem...');
        startJob(job_id, prompt, file.name);
      } catch (err) {
        console.error(err);
        const errorMsg = err.response?.data?.error || err.message || 'Falha ao iniciar o job de upload.';
        setError(errorMsg);
        setIsLoading(false);
      }
    },
    [updateHistory]
  );

  const submitUrlJob = useCallback(
    async (videoUrl, prompt) => {
      setIsLoading(true);
      setError(null); setProgress(0); setDownloadUrl(null); setJobId(null);
      try {
        setStatus('1.5/2: Solicitando job a partir da URL...'); // Corrigido
        const { job_id } = await InternalApiService.startUrlJob({
          video_url: videoUrl, prompt: prompt,
        });
        setStatus('2/2: Aguardando na fila da nuvem...');
        startJob(job_id, prompt, videoUrl);
      } catch (err) {
        console.error(err);
        const errorMsg = err.response?.data?.error || err.message || 'Falha ao iniciar o job de URL.';
        setError(errorMsg);
        setIsLoading(false);
      }
    },
    [updateHistory]
  );

  return {
    isLoading, status, progress, downloadUrl, error, history, 
    submitFileJob, submitUrlJob,
  };
}



