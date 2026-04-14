import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'REFLECT - AI-Powered Sources',
  description: 'Ethical AI-powered source tracking for students with speech-to-text, AI structuring, and semantic search',
  generator: 'v0.app',
  icons: {
    icon: [
      {
            url:'/mind_light.png',
            media:'(prefers-color-scheme: light)',
      },
      {
        url:'/mind_dark.png',
        media:'(prefers-color-scheme: dark)',
      },
      {
        url:'/mind_light.png',
        type:'image/png',
      }
    ]
  }
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
