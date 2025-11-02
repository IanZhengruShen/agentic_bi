export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">Agentic BI Platform</h1>
        <p className="text-xl text-gray-600">
          AI-powered data analysis and visualization
        </p>
        <div className="mt-8 text-sm text-gray-500">
          Backend API: {process.env.NEXT_PUBLIC_API_URL || "Not configured"}
        </div>
      </div>
    </main>
  );
}
