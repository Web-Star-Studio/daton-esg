import {
  startTransition,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from 'react'
import { createPortal } from 'react-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getDocumentDirectoryLabel } from '../constants/document-directories'
import {
  createProjectGenerationThread,
  deleteProjectGenerationThread,
  fetchProjectGenerationThread,
  fetchProjectGenerationThreads,
  streamProjectGenerationMessage,
} from '../services/api-client'
import type {
  ProjectGenerationCitation,
  ProjectGenerationMessage,
  ProjectGenerationThread,
  ProjectRecord,
} from '../types/project'

type AgentDrawerProps = {
  currentProjectId: string
  isLoadingWorkspace: boolean
  isOpen: boolean
  onClose: () => void
  project: ProjectRecord | null
  workspaceError: string | null
}

function formatMessageTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatThreadDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
  }).format(date)
}

function CitationList({
  citations,
}: {
  citations: ProjectGenerationCitation[]
}) {
  if (citations.length === 0) {
    return null
  }

  return (
    <div className="mt-3 border-t border-black/5 pt-2">
      <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#9b9ba1]">
        Evidências utilizadas
      </p>
      <ul className="mt-1.5 space-y-1">
        {citations.map((citation, index) => {
          const label =
            citation.filename === '__project_metadata__'
              ? 'Metadados do projeto'
              : citation.filename
          const directoryLabel = citation.directory_key
            ? (getDocumentDirectoryLabel(citation.directory_key) ??
              citation.directory_key)
            : null
          return (
            <li
              key={`${citation.document_id ?? 'project'}-${citation.chunk_index}-${index}`}
              className="text-[11px] leading-4 tracking-[-0.01em] text-[#6b6b72]"
            >
              <span className="font-medium text-[#1d1d1f]">{label}</span>
              {directoryLabel ? (
                <span className="text-[#9b9ba1]"> · {directoryLabel}</span>
              ) : null}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function AssistantMarkdown({ content }: { content: string }) {
  return (
    <div className="mt-1 text-[13px] leading-[1.55] tracking-[-0.01em] text-[#1d1d1f]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p className="mb-2 last:mb-0 whitespace-pre-wrap">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="mb-2 list-disc space-y-1 pl-4 last:mb-0 marker:text-[#9b9ba1]">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2 list-decimal space-y-1 pl-4 last:mb-0 marker:text-[#9b9ba1]">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="leading-[1.5]">{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold text-[#1d1d1f]">{children}</strong>
          ),
          em: ({ children }) => <em className="italic">{children}</em>,
          h1: ({ children }) => (
            <h3 className="mb-2 text-[14px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">
              {children}
            </h3>
          ),
          h2: ({ children }) => (
            <h3 className="mb-2 text-[13px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">
              {children}
            </h3>
          ),
          h3: ({ children }) => (
            <h3 className="mb-1.5 text-[13px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-[0.04em] text-[#6b6b72]">
              {children}
            </h4>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline decoration-primary/40 underline-offset-2 hover:decoration-primary"
            >
              {children}
            </a>
          ),
          code: ({ children, className }) => {
            const isInline = !className
            if (isInline) {
              return (
                <code className="rounded bg-black/5 px-1 py-0.5 font-mono text-[12px] text-[#1d1d1f]">
                  {children}
                </code>
              )
            }
            return (
              <code className="block whitespace-pre-wrap font-mono text-[12px] leading-5 text-[#1d1d1f]">
                {children}
              </code>
            )
          },
          pre: ({ children }) => (
            <pre className="mb-2 overflow-x-auto rounded-md bg-black/5 px-3 py-2 last:mb-0">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="mb-2 border-l-2 border-black/10 pl-3 text-[#6b6b72] last:mb-0">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-3 border-black/6" />,
          table: ({ children }) => (
            <div className="mb-2 overflow-x-auto last:mb-0">
              <table className="w-full border-collapse text-[12px]">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-black/10 px-2 py-1 text-left font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-black/5 px-2 py-1 align-top">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

function ChatMessage({
  message,
  isStreaming = false,
}: {
  message: ProjectGenerationMessage
  isStreaming?: boolean
}) {
  const isAssistant = message.role === 'assistant'

  if (!isAssistant) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-[16px] bg-[#0f1923] px-3.5 py-2 text-[13px] leading-[1.45] tracking-[-0.01em] text-white">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-baseline gap-2">
        <span className="text-[11px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          Agente
        </span>
        <span className="text-[10px] tracking-[-0.01em] text-[#9b9ba1]">
          {isStreaming ? 'respondendo…' : formatMessageTime(message.created_at)}
        </span>
      </div>
      {message.content ? (
        <AssistantMarkdown content={message.content} />
      ) : (
        <div className="mt-1 text-[13px] leading-[1.55] tracking-[-0.01em] text-[#9b9ba1]">
          {isStreaming ? '…' : ''}
        </div>
      )}
      {!isStreaming ? <CitationList citations={message.citations} /> : null}
    </div>
  )
}

export function AgentDrawer({
  currentProjectId,
  isLoadingWorkspace,
  isOpen,
  onClose,
  project,
  workspaceError,
}: AgentDrawerProps) {
  const [threads, setThreads] = useState<ProjectGenerationThread[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ProjectGenerationMessage[]>([])
  const [composerValue, setComposerValue] = useState('')
  const [streamingAssistantContent, setStreamingAssistantContent] = useState('')
  const [streamingStartedAt, setStreamingStartedAt] = useState<string | null>(
    null
  )
  const [isLoadingThreads, setIsLoadingThreads] = useState(true)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [isCreatingThread, setIsCreatingThread] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [panelError, setPanelError] = useState<string | null>(null)
  const [isThreadPickerOpen, setIsThreadPickerOpen] = useState(false)
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const threadPickerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) {
      return
    }
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  useEffect(() => {
    if (!isOpen) {
      return
    }
    if (!currentProjectId) {
      setThreads([])
      setActiveThreadId(null)
      setMessages([])
      setStreamingAssistantContent('')
      setStreamingStartedAt(null)
      setPanelError('Projeto inválido.')
      setIsLoadingThreads(false)
      return
    }

    let active = true

    async function loadThreads() {
      setIsLoadingThreads(true)
      setPanelError(null)
      setMessages([])
      setStreamingAssistantContent('')
      setStreamingStartedAt(null)

      try {
        const response = await fetchProjectGenerationThreads(currentProjectId)
        if (!active) {
          return
        }
        setThreads(response)
        setActiveThreadId((currentActiveThreadId) => {
          if (
            currentActiveThreadId &&
            response.some((thread) => thread.id === currentActiveThreadId)
          ) {
            return currentActiveThreadId
          }
          return response[0]?.id ?? null
        })
      } catch (error) {
        if (!active) {
          return
        }
        setThreads([])
        setActiveThreadId(null)
        setPanelError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar as conversas do agente.'
        )
      } finally {
        if (active) {
          setIsLoadingThreads(false)
        }
      }
    }

    void loadThreads()

    return () => {
      active = false
    }
  }, [currentProjectId, isOpen])

  useEffect(() => {
    if (!isOpen) {
      return
    }
    if (!currentProjectId || !activeThreadId) {
      setMessages([])
      setStreamingAssistantContent('')
      setStreamingStartedAt(null)
      setIsLoadingMessages(false)
      return
    }

    let active = true
    const currentThreadId = activeThreadId

    async function loadThread() {
      setIsLoadingMessages(true)
      setPanelError(null)
      setStreamingAssistantContent('')
      setStreamingStartedAt(null)

      try {
        const response = await fetchProjectGenerationThread(
          currentProjectId,
          currentThreadId
        )
        if (!active) {
          return
        }
        setMessages(response.messages)
        setThreads((currentThreads) =>
          currentThreads.map((thread) =>
            thread.id === response.thread.id ? response.thread : thread
          )
        )
      } catch (error) {
        if (!active) {
          return
        }
        setMessages([])
        setPanelError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar a conversa.'
        )
      } finally {
        if (active) {
          setIsLoadingMessages(false)
        }
      }
    }

    void loadThread()

    return () => {
      active = false
    }
  }, [activeThreadId, currentProjectId, isOpen])

  useEffect(() => {
    const node = scrollAreaRef.current
    if (!node) {
      return
    }
    node.scrollTop = node.scrollHeight
  }, [messages, streamingAssistantContent])

  useEffect(() => {
    if (!isThreadPickerOpen) {
      setConfirmDeleteId(null)
      return
    }
    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node
      if (
        threadPickerRef.current &&
        !threadPickerRef.current.contains(target)
      ) {
        setIsThreadPickerOpen(false)
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [isThreadPickerOpen])

  const canSend = useMemo(
    () =>
      Boolean(
        currentProjectId &&
          activeThreadId &&
          composerValue.trim() &&
          !isSending &&
          !isLoadingWorkspace &&
          !workspaceError
      ),
    [
      activeThreadId,
      composerValue,
      currentProjectId,
      isLoadingWorkspace,
      isSending,
      workspaceError,
    ]
  )

  const streamingAssistantMessage =
    streamingAssistantContent && activeThreadId && streamingStartedAt
      ? ({
          id: '__streaming__',
          thread_id: activeThreadId,
          project_id: currentProjectId ?? '',
          role: 'assistant',
          content: streamingAssistantContent,
          citations: [],
          created_at: streamingStartedAt,
        } satisfies ProjectGenerationMessage)
      : null

  async function handleCreateThread() {
    if (!currentProjectId || isCreatingThread) {
      return
    }
    setIsCreatingThread(true)
    setPanelError(null)
    setIsThreadPickerOpen(false)

    try {
      const thread = await createProjectGenerationThread(currentProjectId)
      setThreads((currentThreads) => [thread, ...currentThreads])
      setActiveThreadId(thread.id)
      setMessages([])
    } catch (error) {
      setPanelError(
        error instanceof Error
          ? error.message
          : 'Não foi possível criar a conversa.'
      )
    } finally {
      setIsCreatingThread(false)
    }
  }

  async function handleDeleteThread(threadId: string) {
    if (!currentProjectId || deletingThreadId) {
      return
    }
    setDeletingThreadId(threadId)
    setPanelError(null)
    try {
      await deleteProjectGenerationThread(currentProjectId, threadId)
      setThreads((currentThreads) => {
        const remaining = currentThreads.filter(
          (thread) => thread.id !== threadId
        )
        setActiveThreadId((currentActive) => {
          if (currentActive !== threadId) {
            return currentActive
          }
          return remaining[0]?.id ?? null
        })
        return remaining
      })
      setConfirmDeleteId(null)
    } catch (error) {
      setPanelError(
        error instanceof Error
          ? error.message
          : 'Não foi possível remover a conversa.'
      )
    } finally {
      setDeletingThreadId(null)
    }
  }

  async function handleSendMessage() {
    const content = composerValue.trim()
    if (!currentProjectId || !activeThreadId || !content || isSending) {
      return
    }

    setIsSending(true)
    setPanelError(null)
    setComposerValue('')
    setStreamingAssistantContent('')
    setStreamingStartedAt(new Date().toISOString())

    try {
      await streamProjectGenerationMessage(
        currentProjectId,
        activeThreadId,
        { content },
        {
          onThread: (thread) => {
            startTransition(() => {
              setThreads((currentThreads) => {
                const hasThread = currentThreads.some(
                  (currentThread) => currentThread.id === thread.id
                )
                if (!hasThread) {
                  return [thread, ...currentThreads]
                }
                return [
                  thread,
                  ...currentThreads.filter(
                    (currentThread) => currentThread.id !== thread.id
                  ),
                ]
              })
            })
          },
          onUserMessage: (message) => {
            startTransition(() => {
              setMessages((currentMessages) => [...currentMessages, message])
            })
          },
          onToken: (text) => {
            startTransition(() => {
              setStreamingAssistantContent(
                (currentContent) => currentContent + text
              )
            })
          },
          onAssistantMessage: (message) => {
            startTransition(() => {
              setStreamingAssistantContent('')
              setStreamingStartedAt(null)
              setMessages((currentMessages) => [...currentMessages, message])
            })
          },
          onError: (message) => {
            setStreamingAssistantContent('')
            setStreamingStartedAt(null)
            setPanelError(message)
          },
          onDone: () => {
            setStreamingAssistantContent('')
            setStreamingStartedAt(null)
          },
        }
      )
    } catch (error) {
      setStreamingAssistantContent('')
      setStreamingStartedAt(null)
      setPanelError(
        error instanceof Error
          ? error.message
          : 'Não foi possível obter resposta do agente.'
      )
    } finally {
      setIsSending(false)
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (canSend) {
        void handleSendMessage()
      }
    }
  }

  const activeThread = threads.find((thread) => thread.id === activeThreadId)
  const composerDisabled =
    isSending ||
    isLoadingWorkspace ||
    isLoadingThreads ||
    isLoadingMessages ||
    !activeThreadId
  const pickerLabel = activeThread?.title ?? 'Nenhuma conversa'
  const pickerMeta = activeThread
    ? (project?.org_name ?? 'Base vetorial')
    : project
      ? `Base vetorial · ${project.org_name}`
      : 'Base vetorial do projeto'

  if (typeof document === 'undefined') {
    return null
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
        aria-label="Agente"
        aria-modal={false}
        className="pointer-events-auto flex h-full w-[min(440px,100vw)] flex-col border-l border-black/10 bg-white shadow-[-12px_0_40px_rgba(0,0,0,0.08)]"
      >
        <header className="flex items-center gap-2 border-b border-black/6 px-3 py-2.5">
          <div ref={threadPickerRef} className="relative min-w-0 flex-1">
            <button
              type="button"
              onClick={() => {
                if (threads.length === 0) {
                  return
                }
                setIsThreadPickerOpen((current) => !current)
              }}
              disabled={threads.length === 0}
              className="apple-focus-ring flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left transition hover:bg-black/4 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              aria-label="Selecionar conversa"
              aria-expanded={isThreadPickerOpen}
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                  {pickerLabel}
                </div>
                <div className="truncate text-[10px] tracking-[-0.01em] text-[#9b9ba1]">
                  {pickerMeta}
                </div>
              </div>
              {threads.length > 0 ? (
                <span
                  aria-hidden="true"
                  className="material-symbols-outlined shrink-0 text-[14px] text-[#9b9ba1]"
                >
                  expand_more
                </span>
              ) : null}
            </button>
            {isThreadPickerOpen && threads.length > 0 ? (
              <div className="absolute left-0 top-full z-10 mt-1 max-h-[260px] w-full overflow-y-auto rounded-lg border border-black/8 bg-white p-1 shadow-[rgba(0,0,0,0.12)_0px_8px_24px]">
                <ul className="space-y-0.5">
                  {threads.map((thread) => {
                    const isActive = thread.id === activeThreadId
                    const isConfirmingDelete = confirmDeleteId === thread.id
                    const isDeleting = deletingThreadId === thread.id
                    return (
                      <li
                        key={thread.id}
                        className={`group flex items-center gap-1 rounded-md pr-1 transition ${
                          isActive ? 'bg-black/5' : 'hover:bg-black/3'
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => {
                            setActiveThreadId(thread.id)
                            setIsThreadPickerOpen(false)
                          }}
                          disabled={isDeleting}
                          className="flex min-w-0 flex-1 items-baseline justify-between gap-2 rounded-md px-2 py-1.5 text-left transition disabled:opacity-50"
                        >
                          <span
                            className={`truncate text-[12px] tracking-[-0.01em] ${
                              isActive ? 'text-[#1d1d1f]' : 'text-[#3a3a3c]'
                            }`}
                          >
                            {thread.title}
                          </span>
                          <span className="shrink-0 text-[10px] tracking-[-0.01em] text-[#9b9ba1]">
                            {formatThreadDate(thread.updated_at)}
                          </span>
                        </button>
                        {isConfirmingDelete ? (
                          <div className="flex shrink-0 items-center gap-1">
                            <button
                              type="button"
                              onClick={() => {
                                void handleDeleteThread(thread.id)
                              }}
                              disabled={isDeleting}
                              aria-label={`Confirmar exclusão de ${thread.title}`}
                              className="apple-focus-ring rounded px-1.5 py-0.5 text-[10px] font-medium text-[#d01f1f] transition hover:bg-[#fff0f0] disabled:opacity-50"
                            >
                              {isDeleting ? '…' : 'Excluir'}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setConfirmDeleteId(null)
                              }}
                              disabled={isDeleting}
                              aria-label="Cancelar exclusão"
                              className="apple-focus-ring rounded px-1.5 py-0.5 text-[10px] font-medium text-[#86868b] transition hover:bg-black/5 disabled:opacity-50"
                            >
                              Cancelar
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => {
                              setConfirmDeleteId(thread.id)
                            }}
                            aria-label={`Excluir conversa ${thread.title}`}
                            className="apple-focus-ring inline-flex size-6 shrink-0 items-center justify-center rounded text-[#9b9ba1] opacity-0 transition hover:bg-black/5 hover:text-[#d01f1f] focus:opacity-100 group-hover:opacity-100"
                          >
                            <span
                              aria-hidden="true"
                              className="material-symbols-outlined text-[14px]"
                            >
                              delete
                            </span>
                          </button>
                        )}
                      </li>
                    )
                  })}
                </ul>
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => {
              void handleCreateThread()
            }}
            disabled={isCreatingThread || !currentProjectId}
            aria-label="Nova conversa"
            className="apple-focus-ring inline-flex size-8 shrink-0 items-center justify-center rounded-full text-[#1d1d1f] transition hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <span
              aria-hidden="true"
              className="material-symbols-outlined text-[18px]"
            >
              {isCreatingThread ? 'progress_activity' : 'edit_square'}
            </span>
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar agente"
            className="apple-focus-ring inline-flex size-8 shrink-0 items-center justify-center rounded-full text-[#86868b] transition hover:bg-black/5 hover:text-[#1d1d1f]"
          >
            <span
              aria-hidden="true"
              className="material-symbols-outlined text-[18px]"
            >
              close
            </span>
          </button>
        </header>

        {panelError ? (
          <div className="mx-4 mt-3 rounded-md border border-[#ffd0d0] bg-[#fff6f6] px-3 py-2 text-[11px] font-medium tracking-[-0.01em] text-[#d01f1f]">
            {panelError}
          </div>
        ) : null}

        <div
          ref={scrollAreaRef}
          className="min-h-0 flex-1 overflow-y-auto px-4 py-4"
        >
          {isLoadingMessages ? (
            <p className="text-[12px] tracking-[-0.01em] text-[#9b9ba1]">
              Carregando conversa…
            </p>
          ) : !activeThreadId ? (
            <div className="flex h-full min-h-[240px] items-center justify-center text-center">
              <div className="max-w-[280px] space-y-3">
                <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                  Nenhuma conversa ainda.
                </p>
                <p className="text-[12px] leading-5 tracking-[-0.01em] text-[#9b9ba1]">
                  Crie uma conversa para começar a perguntar sobre o projeto
                  {project ? ` ${project.org_name}` : ''}.
                </p>
                <button
                  type="button"
                  disabled={isCreatingThread || !currentProjectId}
                  onClick={() => {
                    void handleCreateThread()
                  }}
                  className="apple-focus-ring mt-1 rounded-full bg-[#0f1923] px-3.5 py-1.5 text-[11px] font-medium text-white transition hover:bg-[#1a2632] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isCreatingThread ? 'Criando…' : 'Criar primeira conversa'}
                </button>
              </div>
            </div>
          ) : messages.length === 0 && !streamingAssistantMessage ? (
            <div className="flex h-full min-h-[240px] items-center justify-center text-center">
              <p className="max-w-[280px] text-[12px] leading-5 tracking-[-0.01em] text-[#9b9ba1]">
                Pergunte algo sobre o projeto. O agente responde apenas com
                base nos documentos indexados.
              </p>
            </div>
          ) : (
            <div className="space-y-5 pb-2">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {streamingAssistantMessage ? (
                <ChatMessage message={streamingAssistantMessage} isStreaming />
              ) : null}
            </div>
          )}
        </div>

        <div className="border-t border-black/5 px-4 py-3">
          <div
            className={`flex items-end gap-2 rounded-2xl border bg-white px-3 py-2 transition ${
              composerDisabled
                ? 'border-black/6'
                : 'border-black/10 focus-within:border-black/25 focus-within:shadow-[0_1px_2px_rgba(0,0,0,0.04)]'
            }`}
          >
            <label htmlFor="agent-composer" className="sr-only">
              Escreva sua mensagem
            </label>
            <textarea
              id="agent-composer"
              value={composerValue}
              onChange={(event) => {
                setComposerValue(event.target.value)
              }}
              onKeyDown={handleComposerKeyDown}
              rows={1}
              placeholder="Pergunte algo sobre o projeto…"
              disabled={composerDisabled}
              className="max-h-[180px] min-h-[24px] flex-1 resize-none border-0 bg-transparent px-1 py-1 text-[13px] leading-5 tracking-[-0.01em] text-[#1d1d1f] placeholder:text-[#9b9ba1] focus:outline-none focus:ring-0 disabled:cursor-not-allowed"
            />
            <button
              type="button"
              disabled={!canSend}
              onClick={() => {
                void handleSendMessage()
              }}
              className="apple-focus-ring shrink-0 rounded-full bg-[#0f1923] px-3 py-1.5 text-[11px] font-medium text-white transition hover:bg-[#1a2632] disabled:cursor-not-allowed disabled:bg-[#c7c7cc]"
            >
              {isSending ? 'Enviando…' : 'Enviar'}
            </button>
          </div>
          <p className="mt-2 px-1 text-[10px] tracking-[-0.01em] text-[#9b9ba1]">
            Responde apenas com base nas evidências do projeto.
          </p>
        </div>
      </div>
    </div>,
    document.body
  )
}
