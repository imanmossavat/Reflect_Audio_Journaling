import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "REFLECT - Audio Journaling",
  description: "A private, secure audio journaling app that helps you reflect on your day - powered by AI."
};

import { ServerStatusProvider } from "@/context/ServerStatusContext";
import { SetupGuard } from "@/components/shared/SetupGuard";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ServerStatusProvider>
          <SetupGuard>
            {children}
          </SetupGuard>
        </ServerStatusProvider>
      </body>
    </html>
  );
}
