const STATUS_LABELS: Record<string, string> = {
  archived: 'Arquivado',
  collecting: 'Em coleta',
  finalized: 'Finalizado',
  generating: 'Em geração',
  reviewing: 'Em revisão',
}

const STATUS_STYLES: Record<string, string> = {
  archived: 'bg-[#f2f2f4] text-[#6e6e73]',
  collecting: 'bg-[#e9f4ff] text-[#0673e0]',
  finalized: 'bg-[#e8f7ee] text-[#14804a]',
  generating: 'bg-[#fff6e5] text-[#9a6700]',
  reviewing: 'bg-[#f3ecff] text-[#6c2bd9]',
}

type ProjectStatusBadgeProps = {
  status: string
}

export function ProjectStatusBadge({ status }: ProjectStatusBadgeProps) {
  const label = STATUS_LABELS[status] ?? status
  const className = STATUS_STYLES[status] ?? 'bg-[#f2f2f4] text-[#1d1d1f]'

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium tracking-[-0.01em] ${className}`}
    >
      {label}
    </span>
  )
}
