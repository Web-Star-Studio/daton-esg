export const ORGANIZATION_SIZE_OPTIONS = [
  { label: 'Selecione o porte', value: '' },
  { label: 'Micro', value: 'micro' },
  { label: 'Pequena', value: 'pequena' },
  { label: 'Média', value: 'média' },
  { label: 'Grande', value: 'grande' },
] as const

export type ProjectFormValues = {
  base_year: string
  org_location: string
  org_name: string
  org_sector: string
  org_size: string
  scope: string
}

export function projectRecordToFormValues(
  project:
    | {
        base_year: number
        org_location: string | null
        org_name: string
        org_sector: string | null
        org_size: string | null
        scope: string | null
      }
    | null
    | undefined
): ProjectFormValues {
  return {
    base_year: project?.base_year != null ? String(project.base_year) : '',
    org_location: project?.org_location ?? '',
    org_name: project?.org_name ?? '',
    org_sector: project?.org_sector ?? '',
    org_size: project?.org_size ?? '',
    scope: project?.scope ?? '',
  }
}
