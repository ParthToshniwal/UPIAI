import './globals.css';

export const metadata = {
  title: 'UPIAI - Universal Personalized Inventory & Demand Intelligence',
  description: 'AI-driven inventory intelligence, multi-horizon demand forecasting, dataset provenance auditing, and automated supplier optimization.',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body className="min-h-screen bg-[#090d16] text-slate-100 antialiased selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
