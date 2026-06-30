import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniFinance: Autonomous Banking & AI Sandbox",
  description: "OmniFinance Digital Wallet Sandbox with AI routing, fraud checking, and financial literacy coaching.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        {/* FontAwesome for icons */}
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
      </head>
      <body>{children}</body>
    </html>
  );
}
