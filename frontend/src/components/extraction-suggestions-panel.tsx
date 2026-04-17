import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'

import { getDocumentDirectoryLabel } from '../constants/document-directories'
import { IconBtn } from './icon-btn'
import { PrimaryBtn } from './primary-btn'
import { SecondaryBtn } from './secondary-btn'
import type {
  ExtractionConfidence,
  ExtractionSuggestion,
  IndicatorValueSuggestionPayload,
  MaterialTopicSuggestionPayload,
  SdgSuggestionPayload,
} from '../types/extraction'

type Props = {
  isOpen: boolean
  onClose: () => void
  title: string
  suggestions: ExtractionSuggestion[]
  isStreaming: boolean
  isLoading: boolean
  error: string | null
  onAccept: (suggestion: ExtractionSuggestion) => void | Promise<void>
  onReject: (suggestion: ExtractionSuggestion) => void | Promise<void>
  onAcceptAll: (ids: string[]) => void | Promise<void>
  onRejectAll: (ids: string[]) => void | Promise<void>
  onStart: () => void
  emptyHint?: string
}

const CONFIDENCE_LABEL: Record<ExtractionConfidence, string> = {
  high: 'Alta',
  medium: 'Média',
  low: 'Baixa',
}

const CONFIDENCE_TONE: Record<ExtractionConfidence, string> = {
  high: 'bg-[#0673e0]/10 text-[#0673e0]',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-black/5 text-[#6b6b72]',
}

function ConfidenceBadge({ value }: { value: ExtractionConfidence }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.06em] ${CONFIDENCE_TONE[value]}`}
    >
      {CONFIDENCE_LABEL[value]}
    </span>
  )
}

function PayloadPreview({ suggestion }: { suggestion: ExtractionSuggestion }) {
  if (suggestion.target_kind === 'material_topic') {
    const payload = suggestion.payload as MaterialTopicSuggestionPayload
    return (
      <div className="space-y-1">
        <div className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          [{payload.pillar}] {payload.topic}
        </div>
        <div className="text-[11px] text-[#6b6b72]">
          Prioridade: {payload.priority}
        </div>
      </div>
    )
  }
  if (suggestion.target_kind === 'sdg_goal') {
    const payload = suggestion.payload as SdgSuggestionPayload
    return (
      <div className="space-y-1">
        <div className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          ODS {payload.ods_number} — {payload.objetivo}
        </div>
        {payload.acao ? (
          <div className="text-[11px] text-[#6b6b72]">{payload.acao}</div>
        ) : null}
      </div>
    )
  }
  if (suggestion.target_kind === 'indicator_value') {
    const payload = suggestion.payload as IndicatorValueSuggestionPayload
    return (
      <div className="space-y-1">
        <div className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          {payload.indicador}
        </div>
        <div className="text-[12px] text-[#1d1d1f]">
          <strong>{payload.value}</strong>{' '}
          <span className="text-[#6b6b72]">{payload.unidade}</span>
          {payload.period ? (
            <span className="text-[#9b9ba1]"> · {payload.period}</span>
          ) : null}
          {payload.scope ? (
            <span className="text-[#9b9ba1]"> · {payload.scope}</span>
          ) : null}
        </div>
        <div className="text-[10px] text-[#9b9ba1]">{payload.tema}</div>
      </div>
    )
  }
  return null
}

function ProvenanceList({ suggestion }: { suggestion: ExtractionSuggestion }) {
  if (suggestion.provenance.length === 0) return null
  return (
    <ul className="mt-2 space-y-1 border-t border-black/6 pt-2">
      {suggestion.provenance.map((item, idx) => (
        <li
          key={`${item.document_id}-${item.chunk_index}-${idx}`}
          className="text-[11px] leading-4 text-[#6b6b72]"
        >
          <div className="text-[#1d1d1f]">
            <span className="font-medium">{item.document_name}</span>
            <span className="text-[#9b9ba1]">
              {' '}
              · trecho #{item.chunk_index}
            </span>
          </div>
          {item.excerpt ? (
            <div className="mt-0.5 italic text-[#6b6b72]">"{item.excerpt}"</div>
          ) : null}
        </li>
      ))}
    </ul>
  )
}

function ConflictBanner({ suggestion }: { suggestion: ExtractionSuggestion }) {
  if (!suggestion.conflict_with_existing) return null
  return (
    <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-900">
      <div className="font-medium">Conflito com valor já preenchido</div>
      {suggestion.existing_value_snapshot ? (
        <pre className="mt-1 whitespace-pre-wrap text-[10px] text-amber-800">
          {JSON.stringify(suggestion.existing_value_snapshot, null, 2)}
        </pre>
      ) : null}
    </div>
  )
}

function SuggestionCard({
  suggestion,
  onAccept,
  onReject,
}: {
  suggestion: ExtractionSuggestion
  onAccept: () => void
  onReject: () => void
}) {
  const directoryLabel = suggestion.provenance[0]?.document_name
    ? (getDocumentDirectoryLabel(suggestion.provenance[0].document_name) ??
      null)
    : null

  return (
    <article className="rounded-[12px] border border-black/8 bg-white p-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      <header className="flex items-start justify-between gap-2">
        <PayloadPreview suggestion={suggestion} />
        <ConfidenceBadge value={suggestion.confidence} />
      </header>
      {directoryLabel ? (
        <div className="mt-1 text-[10px] uppercase tracking-[0.06em] text-[#9b9ba1]">
          {directoryLabel}
        </div>
      ) : null}
      <ConflictBanner suggestion={suggestion} />
      <ProvenanceList suggestion={suggestion} />
      {suggestion.reviewer_notes ? (
        <div className="mt-2 rounded-md bg-amber-50 px-2 py-1 text-[11px] text-amber-900">
          {suggestion.reviewer_notes}
        </div>
      ) : null}
      <footer className="mt-3 flex items-center justify-end gap-2">
        <SecondaryBtn onClick={onReject}>Rejeitar</SecondaryBtn>
        <PrimaryBtn onClick={onAccept}>
          {suggestion.conflict_with_existing ? 'Substituir' : 'Aceitar'}
        </PrimaryBtn>
      </footer>
    </article>
  )
}

export function ExtractionSuggestionsPanel({
  isOpen,
  onClose,
  title,
  suggestions,
  isStreaming,
  isLoading,
  error,
  onAccept,
  onReject,
  onAcceptAll,
  onRejectAll,
  onStart,
  emptyHint,
}: Props) {
  useEffect(() => {
    if (!isOpen) return
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  const pendingIds = useMemo(() => suggestions.map((s) => s.id), [suggestions])
  const [busy, setBusy] = useState(false)

  if (typeof document === 'undefined') return null

  const wrap = async (fn: () => Promise<void> | void) => {
    setBusy(true)
    try {
      await fn()
    } finally {
      setBusy(false)
    }
  }

  return createPortal(
    <div
      className={`pointer-events-none fixed inset-y-0 right-0 z-[9990] flex transition-transform duration-200 ease-out ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
      aria-hidden={!isOpen}
    >
      <div
        role="dialog"
        aria-label={title}
        aria-modal={false}
        className="pointer-events-auto flex h-full w-[min(440px,100vw)] flex-col border-l border-black/10 bg-[#f5f7f8] shadow-[-12px_0_40px_rgba(0,0,0,0.08)]"
      >
        <header className="flex items-center justify-between gap-2 border-b border-black/6 bg-white px-4 py-3">
          <div className="min-w-0">
            <h2 className="text-[14px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">
              {title}
            </h2>
            <p className="text-[11px] text-[#6b6b72]">
              {isStreaming
                ? 'Extraindo dos documentos…'
                : suggestions.length > 0
                  ? `${suggestions.length} sugestão(ões) para revisar`
                  : 'Nenhuma sugestão pendente'}
            </p>
          </div>
          <IconBtn onClick={onClose} aria-label="Fechar painel de sugestões">
            <span className="material-symbols-outlined text-[18px]" aria-hidden>
              close
            </span>
          </IconBtn>
        </header>

        <div className="flex items-center gap-2 border-b border-black/6 bg-white px-4 py-2">
          <PrimaryBtn
            onClick={onStart}
            disabled={isStreaming}
            data-testid="extraction-start"
          >
            {isStreaming ? 'Extraindo…' : 'Auto-preencher com IA'}
          </PrimaryBtn>
          {suggestions.length > 0 ? (
            <>
              <SecondaryBtn
                disabled={busy}
                onClick={() => void wrap(() => onAcceptAll(pendingIds))}
              >
                Aceitar todas
              </SecondaryBtn>
              <SecondaryBtn
                disabled={busy}
                onClick={() => void wrap(() => onRejectAll(pendingIds))}
              >
                Rejeitar todas
              </SecondaryBtn>
            </>
          ) : null}
        </div>

        {error ? (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-[12px] text-amber-900">
            {error}
          </div>
        ) : null}

        <div className="flex-1 space-y-2 overflow-y-auto px-4 py-3">
          {isLoading ? (
            <p className="text-[12px] text-[#6b6b72]">Carregando sugestões…</p>
          ) : suggestions.length === 0 ? (
            <p className="text-[12px] text-[#6b6b72]">
              {emptyHint ??
                'Quando você executar a extração, as sugestões aparecerão aqui.'}
            </p>
          ) : (
            suggestions.map((suggestion) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onAccept={() => void onAccept(suggestion)}
                onReject={() => void onReject(suggestion)}
              />
            ))
          )}
        </div>
      </div>
    </div>,
    document.body
  )
}
