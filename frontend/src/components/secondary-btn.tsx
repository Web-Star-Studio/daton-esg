import type { ButtonHTMLAttributes, ReactNode } from 'react'

type SecondaryBtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode
}

const SECONDARY_BTN_BASE_CLASSNAME =
  'apple-focus-ring mt-4 inline-flex items-center justify-center rounded-[0.7rem] bg-[#e8e8ed] px-3 py-1 text-sm font-medium text-[#1d1d1f] transition-colors hover:bg-[#f5f7f8]'

export function SecondaryBtn({
  children,
  className,
  disabled,
  type = 'button',
  ...props
}: SecondaryBtnProps) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={[
        SECONDARY_BTN_BASE_CLASSNAME,
        disabled ? 'cursor-not-allowed opacity-60 hover:bg-[#e8e8ed]' : null,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...props}
    >
      {children}
    </button>
  )
}
