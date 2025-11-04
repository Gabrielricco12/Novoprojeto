import { useState } from 'react';
// IMPORTAÇÃO CORRIGIDA: Agora do arquivo .js (sem as chaves de tipo)
import { useVideoProcessor } from '../hooks/useVideoProcessor'; 
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ProgressBar } from '../components/ui/ProgressBar';
import { StatusMessage } from '../components/ui/StatusMessage';

// --- Sub-componente: Formulário Principal ---
function JobForm() {
  const [tab, setTab] = useState('upload');
  const [prompt, setPrompt] = useState('');
  const [file, setFile] = useState(null); // File: tipo nativo
  const [url, setUrl] = useState('');

  const {
    isLoading,
    status,
    progress,
    downloadUrl,
    error,
    submitFileJob,
    submitUrlJob,
  } = useVideoProcessor();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt) {
      alert('Por favor, digite um prompt.');
      return;
    }

    if (tab === 'upload' && file) {
      submitFileJob(file, prompt);
    } else if (tab === 'url' && url) {
      submitUrlJob(url, prompt);
    }
  };

  return (
    <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-md">
      <h1 className="mb-6 text-center text-3xl font-bold text-gray-800">
        Editor de Vídeo com IA
      </h1>

      {/* --- Abas (Tabs) --- */}
      <div className="mb-4 flex rounded-md border border-gray-300 p-1">
        <button
          onClick={() => setTab('upload')}
          className={`flex-1 rounded-md px-3 py-2 text-center font-medium transition-all
            ${tab === 'upload' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'}`}
        >
          Fazer Upload
        </button>
        <button
          onClick={() => setTab('url')}
          className={`flex-1 rounded-md px-3 py-2 text-center font-medium transition-all
            ${tab === 'url' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'}`}
        >
          Colar Link (YouTube, etc)
        </button>
      </div>

      {/* --- Formulário Principal --- */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* --- Painel de Upload --- */}
        <div style={{ display: tab === 'upload' ? 'block' : 'none' }}>
          <label htmlFor="file-upload" className="mb-2 block font-medium text-gray-700">
            1. Escolha o arquivo de vídeo:
          </label>
          <Input
            type="file"
            id="file-upload"
            accept="video/*"
            onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
            disabled={isLoading}
            className="file:mr-4 file:rounded-full file:border-0 
                       file:bg-blue-50 file:px-4 file:py-2
                       file:text-sm file:font-semibold file:text-blue-700
                       hover:file:bg-blue-100"
          />
        </div>

        {/* --- Painel de URL --- */}
        <div style={{ display: tab === 'url' ? 'block' : 'none' }}>
          <label htmlFor="url-input" className="mb-2 block font-medium text-gray-700">
            1. Cole o link do vídeo:
          </label>
          <Input
            type="url"
            id="url-input"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isLoading}
          />
        </div>

        {/* --- Prompt (Comum aos dois) --- */}
        <div>
          <label htmlFor="prompt-input" className="mb-2 block font-medium text-gray-700">
            2. O que você quer cortar?
          </label>
          <Input
            type="text"
            id="prompt-input"
            placeholder="Ex: 'um pássaro voando' ou 'cenas com um carro vermelho'"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isLoading}
          />
        </div>

        {/* --- Botão de Envio --- */}
        <Button type="submit" disabled={isLoading || (tab === 'upload' && !file) || (tab === 'url' && !url) || !prompt}>
          {isLoading ? 'Processando...' : 'Iniciar Processo'}
        </Button>
      </form>

      {/* --- Área de Status (Feedback) --- */}
      <div className="mt-6 min-h-[60px] space-y-3">
        {/* Mostra a barra de progresso SÓ durante o upload */}
        {isLoading && status.includes('upload') && <ProgressBar progress={progress} />}
        
        {/* Mostra erros */}
        {error && <StatusMessage message={error} type="error" />}
        
        {/* Mostra status de progresso */}
        {isLoading && !error && <StatusMessage message={status} type="info" />}
        
        {/* Mostra o link de download */}
        {downloadUrl && (
          <StatusMessage message="Seu vídeo está pronto!" type="success">
            <a
              href={downloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 block font-bold text-green-800 underline hover:text-green-900"
            >
              Clique aqui para baixar
            </a>
          </StatusMessage>
        )}
      </div>
    </div>
  );
}

// --- Sub-componente: Histórico ---
function HistoryList() {
  const { history } = useVideoProcessor(); 

  if (history.length === 0) {
    return (
      <div className="mt-6 text-center text-gray-500">
        Nenhum job processado nesta sessão.
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-md">
      <h2 className="mb-4 text-xl font-bold text-gray-800">Histórico de Jobs</h2>
      <ul className="space-y-4">
        {history.map((item) => (
          <li key={item.jobId} className="rounded-md border border-gray-200 p-4">
            <p className="truncate font-semibold text-gray-700" title={item.fileNameOrUrl}>
              <span className="text-sm font-normal text-gray-500">Arquivo:</span> {item.fileNameOrUrl}
            </p>
            <p className="text-gray-600">
              <span className="text-sm font-normal text-gray-500">Prompt:</span> {item.prompt}
            </p>
            <div className="mt-2">
              {item.status === 'Completo' && item.resultUrl && (
                <a href={item.resultUrl} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-600 hover:underline">
                  Baixar Resultado
                </a>
              )}
              {item.status === 'Falhou' && (
                <span className="font-medium text-red-600">Falhou: {item.error}</span>
              )}
              {item.status !== 'Completo' && item.status !== 'Falhou' && (
                <span className="font-medium text-yellow-600">Status: {item.status}...</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// --- Montagem final da página ---
export function HomePage() {
  return (
    <div className="flex w-full max-w-2xl flex-col space-y-8">
      <JobForm />
      <HistoryList />
    </div>
  );
}