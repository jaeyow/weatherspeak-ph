import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Header from '@/components/Header';
import LocationOnboarding from '@/components/LocationOnboarding';
import LanguageProvider from '@/components/LanguageProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'WeatherSpeak PH',
  description: 'PAGASA typhoon bulletins in Tagalog, Cebuano, and English',
  manifest: '/manifest.json',
  themeColor: '#0a0a0f',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-950 text-white min-h-screen`}>
        <LanguageProvider>
          <Header />
          <LocationOnboarding />
          <main className="max-w-lg mx-auto px-4 py-6">{children}</main>
        </LanguageProvider>
      </body>
    </html>
  );
}
