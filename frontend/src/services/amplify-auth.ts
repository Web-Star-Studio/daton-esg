import { Amplify } from 'aws-amplify'
import {
  confirmSignIn,
  fetchAuthSession,
  signIn,
  signOut,
  type AuthSession,
} from 'aws-amplify/auth'
import type { AuthSignInResult, AuthTokens } from '../types/auth'

type CognitoFrontendConfig = {
  region: string
  userPoolId: string
  userPoolClientId: string
}

let isConfigured = false

function getFrontendCognitoConfig(): CognitoFrontendConfig | null {
  const region = import.meta.env.VITE_AWS_COGNITO_REGION?.trim()
  const userPoolId = import.meta.env.VITE_AWS_COGNITO_USER_POOL_ID?.trim()
  const userPoolClientId =
    import.meta.env.VITE_AWS_COGNITO_APP_CLIENT_ID?.trim()

  if (!region || !userPoolId || !userPoolClientId) {
    return null
  }

  return {
    region,
    userPoolId,
    userPoolClientId,
  }
}

export function isAmplifyAuthConfigured() {
  return getFrontendCognitoConfig() !== null
}

export function configureAmplifyAuth() {
  if (isConfigured) {
    return
  }

  const config = getFrontendCognitoConfig()

  if (!config) {
    return
  }

  Amplify.configure(
    {
      Auth: {
        Cognito: {
          userPoolId: config.userPoolId,
          userPoolClientId: config.userPoolClientId,
          loginWith: {
            email: true,
          },
        },
      },
    },
    { ssr: false }
  )

  isConfigured = true
}

function ensureConfigured() {
  configureAmplifyAuth()

  if (!isAmplifyAuthConfigured()) {
    throw new Error(
      'Configuração do Cognito ausente. Preencha VITE_AWS_COGNITO_REGION, VITE_AWS_COGNITO_USER_POOL_ID e VITE_AWS_COGNITO_APP_CLIENT_ID no .env.'
    )
  }
}

function mapSessionTokens(session: AuthSession): AuthTokens {
  return {
    accessToken: session.tokens?.accessToken?.toString() ?? null,
    idToken: session.tokens?.idToken?.toString() ?? null,
  }
}

export async function getCurrentAuthTokens() {
  ensureConfigured()
  const session = await fetchAuthSession()
  return mapSessionTokens(session)
}

/**
 * Ask Amplify for the current tokens, letting it transparently refresh
 * when the access/id token is near expiry. Returns null when there is
 * no valid session (user should re-login).
 */
export async function refreshAuthTokens(): Promise<AuthTokens | null> {
  if (!isAmplifyAuthConfigured()) return null
  try {
    ensureConfigured()
    const session = await fetchAuthSession({ forceRefresh: false })
    const tokens = mapSessionTokens(session)
    if (!tokens.accessToken && !tokens.idToken) return null
    return tokens
  } catch {
    return null
  }
}

function mapAdditionalSignInStep(nextStep?: string): never {
  if (
    nextStep === 'CONFIRM_SIGN_IN_WITH_SMS_CODE' ||
    nextStep === 'CONFIRM_SIGN_IN_WITH_TOTP_CODE'
  ) {
    throw new Error('Sua conta exige MFA para concluir a autenticação.')
  }

  if (
    nextStep === 'CONTINUE_SIGN_IN_WITH_EMAIL_SETUP' ||
    nextStep === 'CONTINUE_SIGN_IN_WITH_MFA_SELECTION' ||
    nextStep === 'CONTINUE_SIGN_IN_WITH_FIRST_FACTOR_SELECTION' ||
    nextStep === 'CONFIRM_SIGN_UP'
  ) {
    throw new Error(
      'Sua conta exige uma etapa adicional de verificação antes do acesso.'
    )
  }

  throw new Error(
    nextStep
      ? `Fluxo de autenticação adicional não suportado nesta fase: ${nextStep}.`
      : 'Fluxo de autenticação adicional não suportado nesta fase.'
  )
}

export async function signInWithEmailPassword(
  email: string,
  password: string
): Promise<AuthSignInResult> {
  ensureConfigured()

  const result = await signIn({
    username: email,
    password,
  })

  if (!result.isSignedIn) {
    const nextStep = result.nextStep?.signInStep

    if (nextStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
      return {
        status: 'new-password-required',
        challenge: {
          type: 'NEW_PASSWORD_REQUIRED',
          email,
        },
      }
    }

    mapAdditionalSignInStep(nextStep)
  }

  const session = await fetchAuthSession()
  return {
    status: 'signed-in',
    tokens: mapSessionTokens(session),
  }
}

export async function completeNewPasswordChallenge(newPassword: string) {
  ensureConfigured()

  const result = await confirmSignIn({
    challengeResponse: newPassword,
  })

  if (!result.isSignedIn) {
    mapAdditionalSignInStep(result.nextStep?.signInStep)
  }

  const session = await fetchAuthSession()
  return mapSessionTokens(session)
}

export async function signOutFromCognito() {
  ensureConfigured()
  await signOut()
}
