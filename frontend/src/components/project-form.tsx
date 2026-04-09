import { useMemo, useState } from 'react'
import {
  ORGANIZATION_SIZE_OPTIONS,
  type ProjectFormValues,
} from './project-form.utils'
import { PrimaryBtn } from './primary-btn'
import { SecondaryBtn } from './secondary-btn'
import type { ProjectCreateInput } from '../types/project'

type ProjectFormProps = {
  cancelLabel?: string
  errorMessage?: string | null
  initialValues: ProjectFormValues
  isSubmitting?: boolean
  onCancel?: () => void
  onSubmit: (payload: ProjectCreateInput) => Promise<void>
  submitLabel: string
}

function normalizeOptionalText(value: string) {
  const normalized = value.trim()
  return normalized.length > 0 ? normalized : null
}

export function ProjectForm({
  cancelLabel,
  errorMessage = null,
  initialValues,
  isSubmitting = false,
  onCancel,
  onSubmit,
  submitLabel,
}: ProjectFormProps) {
  const [values, setValues] = useState<ProjectFormValues>(initialValues)
  const [validationError, setValidationError] = useState<string | null>(null)

  const displayError = validationError ?? errorMessage
  const currentYear = useMemo(() => new Date().getFullYear() + 1, [])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!values.org_name.trim()) {
      setValidationError('Informe o nome da organização.')
      return
    }

    const parsedBaseYear = Number(values.base_year)

    if (!Number.isInteger(parsedBaseYear) || parsedBaseYear < 2000) {
      setValidationError('Informe um ano-base válido.')
      return
    }

    if (parsedBaseYear > currentYear) {
      setValidationError('O ano-base não pode estar no futuro.')
      return
    }

    setValidationError(null)

    await onSubmit({
      base_year: parsedBaseYear,
      org_location: normalizeOptionalText(values.org_location),
      org_name: values.org_name.trim(),
      org_sector: normalizeOptionalText(values.org_sector),
      org_size: normalizeOptionalText(values.org_size),
      scope: normalizeOptionalText(values.scope),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span className="text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Nome da organização
          </span>
          <input
            type="text"
            value={values.org_name}
            onChange={(event) => {
              setValues((current) => ({
                ...current,
                org_name: event.target.value,
              }))
            }}
            className="apple-focus-ring w-full rounded border border-[#d2d2d7] bg-white px-4 py-2.5 text-[13px] tracking-[-0.01em] text-[#1d1d1f]"
            placeholder="Ex.: Acme Inc."
          />
        </label>

        <label className="space-y-2">
          <span className="text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Setor
          </span>
          <input
            type="text"
            value={values.org_sector}
            onChange={(event) => {
              setValues((current) => ({
                ...current,
                org_sector: event.target.value,
              }))
            }}
            className="apple-focus-ring w-full rounded border border-[#d2d2d7] bg-white px-4 py-2.5 text-[13px] tracking-[-0.01em] text-[#1d1d1f]"
            placeholder="Ex.: Energia"
          />
        </label>

        <label className="space-y-2">
          <span className="text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Porte
          </span>
          <select
            value={values.org_size}
            onChange={(event) => {
              setValues((current) => ({
                ...current,
                org_size: event.target.value,
              }))
            }}
            className="apple-focus-ring w-full rounded border border-[#d2d2d7] bg-white px-4 py-2.5 text-[13px] tracking-[-0.01em] text-[#1d1d1f]"
          >
            {ORGANIZATION_SIZE_OPTIONS.map((option) => (
              <option key={option.value || 'placeholder'} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2">
          <span className="text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Localização
          </span>
          <input
            type="text"
            value={values.org_location}
            onChange={(event) => {
              setValues((current) => ({
                ...current,
                org_location: event.target.value,
              }))
            }}
            className="apple-focus-ring w-full rounded border border-[#d2d2d7] bg-white px-4 py-2.5 text-[13px] tracking-[-0.01em] text-[#1d1d1f]"
            placeholder="Ex.: Recife, PE"
          />
        </label>

        <label className="space-y-2">
          <span className="text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Ano-base
          </span>
          <input
            type="number"
            inputMode="numeric"
            value={values.base_year}
            onChange={(event) => {
              setValues((current) => ({
                ...current,
                base_year: event.target.value,
              }))
            }}
            className="apple-focus-ring w-full rounded border border-[#d2d2d7] bg-white px-4 py-2.5 text-[13px] tracking-[-0.01em] text-[#1d1d1f]"
            placeholder="2025"
          />
        </label>
      </div>

      <label className="space-y-2">
        <span className="text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          Abrangência
        </span>
        <textarea
          value={values.scope}
          onChange={(event) => {
            setValues((current) => ({
              ...current,
              scope: event.target.value,
            }))
          }}
          rows={5}
          className="apple-focus-ring w-full rounded border border-[#d2d2d7] bg-white px-4 py-3 text-[13px] tracking-[-0.01em] text-[#1d1d1f]"
          placeholder="Ex.: Operações Brasil, escritórios e planta industrial."
        />
      </label>

      {displayError ? (
        <div className="rounded border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {displayError}
        </div>
      ) : null}

      <div className="flex justify-end gap-3">
        {onCancel ? (
          <SecondaryBtn
            type="button"
            onClick={onCancel}
            className="mt-0 px-3 py-2.5 text-[13px] tracking-[-0.01em]"
          >
            {cancelLabel ?? 'Cancelar'}
          </SecondaryBtn>
        ) : null}
        <PrimaryBtn
          type="submit"
          disabled={isSubmitting}
          className="mt-0 px-4 py-2.5 text-[13px] tracking-[-0.01em] hover:bg-[#0962ba] disabled:hover:bg-primary"
        >
          {isSubmitting ? 'Salvando...' : submitLabel}
        </PrimaryBtn>
      </div>
    </form>
  )
}
