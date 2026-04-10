const STAGES = [
  { label: 'Planejamento', value: 'planning' },
  { label: 'Coleta', value: 'collecting' },
  { label: 'Análise', value: 'analyzing' },
  { label: 'Rel. Preliminar', value: 'preliminary_report' },
  { label: 'Rel. Final', value: 'final_report' },
  { label: 'Ajustes', value: 'alignment' },
  { label: 'Diagramação', value: 'layout' },
] as const

type ProjectTimelineProps = {
  currentStatus: string
  disabled?: boolean
  onStatusChange?: (status: string) => void
}

export function ProjectTimeline({
  currentStatus,
  disabled = false,
  onStatusChange,
}: ProjectTimelineProps) {
  if (currentStatus === 'archived') {
    return (
      <span className="inline-flex items-center rounded-full bg-[#f2f2f4] px-2.5 py-1 text-[11px] font-medium tracking-[-0.01em] text-[#6e6e73]">
        Arquivado
      </span>
    )
  }

  const currentIndex = STAGES.findIndex((s) => s.value === currentStatus)

  return (
    <div className="flex items-start">
      {STAGES.map((stage, index) => {
        const isCompleted = currentIndex > index
        const isCurrent = currentIndex === index
        const isClickable = !disabled && onStatusChange

        return (
          <div key={stage.value} className="flex items-start">
            <button
              type="button"
              disabled={disabled || !onStatusChange}
              onClick={() => {
                onStatusChange?.(stage.value)
              }}
              className={`group flex flex-col items-center gap-1.5 ${isClickable ? 'cursor-pointer' : 'cursor-default'}`}
            >
              <div
                className={`flex size-7 items-center justify-center rounded-full border-2 text-[10px] font-semibold transition-colors ${
                  isCurrent
                    ? 'border-primary bg-primary text-white'
                    : isCompleted
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-[#d2d2d7] bg-white text-[#86868b]'
                } ${isClickable ? 'group-hover:border-primary/70' : ''}`}
              >
                {isCompleted ? (
                  <span className="material-symbols-outlined text-[14px]">
                    check
                  </span>
                ) : (
                  index + 1
                )}
              </div>
              <span
                className={`max-w-[72px] text-center text-[10px] leading-tight tracking-[-0.01em] ${
                  isCurrent
                    ? 'font-semibold text-primary'
                    : isCompleted
                      ? 'font-medium text-[#1d1d1f]'
                      : 'font-medium text-[#86868b]'
                }`}
              >
                {stage.label}
              </span>
            </button>

            {index < STAGES.length - 1 ? (
              <div
                className={`mt-[13px] h-0.5 w-5 flex-shrink-0 ${
                  currentIndex > index ? 'bg-primary' : 'bg-[#d2d2d7]'
                }`}
              />
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
