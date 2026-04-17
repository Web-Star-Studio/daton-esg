import type { ButtonHTMLAttributes, ReactNode } from 'react'

type IconBtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode
}

const ICON_BTN_BASE_CLASSNAME =
  'apple-focus-ring inline-flex items-center justify-center rounded-md p-1 text-[#6b6b72] transition-colors hover:bg-black/5'

export function IconBtn({
  children,
  className,
  disabled,
  type = 'button',
  ...props
}: IconBtnProps) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={[
        ICON_BTN_BASE_CLASSNAME,
        disabled ? 'cursor-not-allowed opacity-60 hover:bg-transparent' : null,
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
