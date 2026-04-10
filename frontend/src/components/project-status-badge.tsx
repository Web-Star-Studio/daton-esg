const STATUS_LABELS: Record<string, string> = {
  alignment: 'Ajustes',
  analyzing: 'Análise',
  archived: 'Arquivado',
  collecting: 'Coleta',
  final_report: 'Rel. Final',
  layout: 'Diagramação',
  planning: 'Planejamento',
  preliminary_report: 'Rel. Preliminar',
}

const STATUS_STYLES: Record<string, string> = {
  alignment: 'bg-[#f3ecff] text-[#6c2bd9]',
  analyzing: 'bg-[#fff6e5] text-[#9a6700]',
  archived: 'bg-[#f2f2f4] text-[#6e6e73]',
  collecting: 'bg-[#e9f4ff] text-[#0673e0]',
  final_report: 'bg-[#e0f2fe] text-[#0c5a97]',
  layout: 'bg-[#e8f7ee] text-[#14804a]',
  planning: 'bg-[#f5f5f7] text-[#1d1d1f]',
  preliminary_report: 'bg-[#fef3e0] text-[#b45309]',
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
