import type { ChangeEvent, DragEvent, RefObject } from 'react'

export type PendingUpload = {
  error?: string
  fileName: string
  id: string
  progress: number
  status: 'uploading' | 'error'
}

type FileUploaderProps = {
  disabled?: boolean
  inputRef: RefObject<HTMLInputElement | null>
  onFilesSelected: (files: File[]) => void
  uploads: PendingUpload[]
  validationMessage: string | null
}

export function FileUploader({
  disabled = false,
  inputRef,
  onFilesSelected,
  uploads,
  validationMessage,
}: FileUploaderProps) {
  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) {
      return
    }

    onFilesSelected(Array.from(files))
  }

  function handleDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault()
    if (disabled) {
      return
    }

    handleFiles(event.dataTransfer.files)
  }

  return (
    <section className="space-y-4">
      <button
        type="button"
        onClick={() => {
          inputRef.current?.click()
        }}
        onDragOver={(event) => {
          event.preventDefault()
        }}
        onDrop={handleDrop}
        className="apple-focus-ring flex w-full flex-col items-start gap-3 rounded-lg border border-dashed border-[#d2d2d7] bg-[#f5f7f8] px-5 py-6 text-left transition-colors hover:border-primary/40 hover:bg-primary/5 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={disabled}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.xlsx,.csv,.docx"
          className="hidden"
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            handleFiles(event.target.files)
            event.target.value = ''
          }}
        />
        <span className="inline-flex size-10 items-center justify-center rounded-[0.7rem] bg-white text-primary shadow-sm">
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[20px]"
          >
            upload_file
          </span>
        </span>
        <div className="space-y-1">
          <p className="text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Arraste arquivos aqui ou clique para selecionar
          </p>
          <p className="text-[12px] tracking-[-0.01em] text-[#86868b]">
            Tipos aceitos: PDF, XLSX, CSV e DOCX. Limite de 50MB por arquivo.
          </p>
        </div>
      </button>

      {validationMessage ? (
        <p className="text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {validationMessage}
        </p>
      ) : null}

      {uploads.length > 0 ? (
        <div className="space-y-2">
          {uploads.map((upload) => (
            <div
              key={upload.id}
              className="rounded-lg border border-black/6 bg-white px-4 py-3"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                    {upload.fileName}
                  </p>
                  <p className="text-[12px] tracking-[-0.01em] text-[#86868b]">
                    {upload.status === 'error'
                      ? (upload.error ?? 'Falha no upload')
                      : `${upload.progress}% enviado`}
                  </p>
                </div>
                <span className="text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                  {upload.progress}%
                </span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#e8e8ed]">
                <div
                  className={`h-full rounded-full transition-all ${
                    upload.status === 'error' ? 'bg-[#d01f1f]' : 'bg-primary'
                  }`}
                  style={{ width: `${upload.progress}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}
