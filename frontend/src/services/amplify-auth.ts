import { Amplify } from 'aws-amplify'
import {
  fetchAuthSession,
  signIn,
  signOut,
  type AuthSession,
} from 'aws-amplify/auth'
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito'
import { sharedInMemoryStorage } from 'aws-amplify/utils'
import type { AuthTokens } from '../types/auth'

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

  cognitoUserPoolsTokenProvider.setKeyValueStorage(sharedInMemoryStorage)

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

export async function signInWithEmailPassword(email: string, password: string) {
  ensureConfigured()

  const result = await signIn({
    username: email,
    password,
  })

  if (!result.isSignedIn) {
    const nextStep = result.nextStep?.signInStep

    if (nextStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
      throw new Error(
        'Sua conta exige definição de nova senha antes do acesso.'
      )
    }

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

  const session = await fetchAuthSession()
  return mapSessionTokens(session)
}

export async function signOutFromCognito() {
  ensureConfigured()
  await signOut()
}
