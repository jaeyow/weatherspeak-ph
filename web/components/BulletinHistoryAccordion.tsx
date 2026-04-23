'use client';

import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface BulletinHistoryItem {
  id: string;
  bulletin_number: number | null;
  pdf_url: string | null;
}

interface Props {
  bulletins: BulletinHistoryItem[];
  stormName: string;
}

export default function BulletinHistoryAccordion({ bulletins, stormName }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleToggle = (id: string) => {
    setExpandedId(prev => prev === id ? null : id);
  };

  return (
    <div className="space-y-1">
      {bulletins.map(bulletin => {
        const isExpanded = expandedId === bulletin.id;
        const hasPdf = !!bulletin.pdf_url;

        return (
          <div key={bulletin.id} className="rounded-lg bg-white/5 overflow-hidden">
            {/* Header - always clickable */}
            <button
              onClick={() => hasPdf && handleToggle(bulletin.id)}
              disabled={!hasPdf}
              className={`
                w-full flex justify-between items-center px-4 py-2.5 text-left
                ${hasPdf ? 'hover:bg-white/10 cursor-pointer' : 'opacity-50 cursor-not-allowed'}
                transition-colors
              `}
            >
              <span className="text-sm text-white">
                Bulletin #{bulletin.bulletin_number}
              </span>
              {hasPdf && (
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              )}
            </button>

            {/* Expandable content */}
            {isExpanded && hasPdf && (
              <div className="border-t border-white/10 p-4 bg-black/20">
                <div className="space-y-3">
                  {/* PDF Preview */}
                  <div className="rounded-lg overflow-hidden bg-white/5">
                    <Document
                      file={bulletin.pdf_url}
                      loading={
                        <div className="flex items-center justify-center h-96 text-gray-400">
                          <div className="flex flex-col items-center gap-2">
                            <svg className="animate-spin h-8 w-8" viewBox="0 0 24 24">
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                                fill="none"
                              />
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              />
                            </svg>
                            <span className="text-sm">Loading PDF...</span>
                          </div>
                        </div>
                      }
                      error={
                        <div className="flex items-center justify-center h-96 text-red-400">
                          <div className="text-center">
                            <p className="text-sm">Failed to load PDF</p>
                            <p className="text-xs text-gray-500 mt-1">Try downloading instead</p>
                          </div>
                        </div>
                      }
                      onLoadError={(error) => console.error('PDF load error:', error)}
                    >
                      <Page
                        pageNumber={1}
                        width={typeof window !== 'undefined' ? Math.min(window.innerWidth - 64, 800) : 800}
                        renderTextLayer={false}
                        renderAnnotationLayer={false}
                        className="mx-auto"
                      />
                    </Document>
                  </div>

                  {/* Download button */}
                  <div className="flex justify-center">
                    <a
                      href={bulletin.pdf_url}
                      download={`${stormName}_Bulletin_${bulletin.bulletin_number}.pdf`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-sm text-white"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download Full PDF
                    </a>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
