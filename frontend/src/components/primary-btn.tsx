import type { ButtonHTMLAttributes, ReactNode } from 'react'

type PrimaryBtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode
}

const PRIMARY_BTN_BASE_CLASSNAME =
  'apple-focus-ring inline-flex items-center justify-center rounded-[0.7rem] bg-primary px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-[#0962ba]'

export function PrimaryBtn({
  children,
  className,
  disabled,
  type = 'button',
  ...props
}: PrimaryBtnProps) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={[
        PRIMARY_BTN_BASE_CLASSNAME,
        className,
        disabled
          ? 'cursor-not-allowed bg-[#8e8e93] text-white opacity-100 hover:bg-[#8e8e93]'
          : null,
      ]
        .filter(Boolean)
        .join(' ')}
      {...props}
    >
      {children}
    </button>
  )
}
