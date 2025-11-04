import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HomePage } from './pages/HomePage' // <-- Vamos criar este arquivo em breve

// Cria uma instância única do "cliente" do React Query
const queryClient = new QueryClient()

function App() {
  return (
    // 1. "Envolve" todo o app com o Provedor do React Query.
    // Isso permite que qualquer componente filho (como nossos hooks)
    // use as funções do React Query (useQuery, etc.)
    <QueryClientProvider client={queryClient}>
      
      {/* 2. Define o layout de fundo da página inteira usando Tailwind */}
      <div className="flex min-h-screen w-full flex-col items-center bg-gray-100 p-4 pt-10 text-gray-900">
        
        {/* 3. Renderiza nossa página principal */}
        {/* (O VS Code vai sublinhar 'HomePage' em vermelho porque ainda não o criamos. Isso é normal.) */}
        <HomePage />
      </div>

    </QueryClientProvider>
  )
}

export default App
