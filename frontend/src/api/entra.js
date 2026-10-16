import { InteractionRequiredAuthError, PublicClientApplication } from '@azure/msal-browser'

const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
let configPromise
let clientPromise

export function loadAuthConfig() {
  if (!configPromise) {
    configPromise = fetch(`${base}/api/auth/config`, { cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) throw new Error('Unable to load authentication configuration')
        return response.json()
      })
      .catch((error) => {
        configPromise = undefined
        throw error
      })
  }
  return configPromise
}

async function entraClient(config) {
  if (config.mode !== 'entra') return null
  if (!config.tenant_id || !config.spa_client_id || !config.api_scope) {
    throw new Error('Microsoft Entra sign-in is not fully configured')
  }
  if (!clientPromise) {
    clientPromise = PublicClientApplication.createPublicClientApplication({
      auth: {
        clientId: config.spa_client_id,
        authority: `https://login.microsoftonline.com/${config.tenant_id}`,
        redirectUri: window.location.origin,
      },
      cache: { cacheLocation: 'sessionStorage' },
    }).catch((error) => {
      clientPromise = undefined
      throw error
    })
  }
  const client = await clientPromise
  if (!client.getActiveAccount()) {
    const account = client.getAllAccounts()[0]
    if (account) client.setActiveAccount(account)
  }
  return client
}

export async function entraAccessToken() {
  const config = await loadAuthConfig()
  if (config.mode !== 'entra') return sessionStorage.getItem('aigovern-token') || ''
  const client = await entraClient(config)
  const account = client.getActiveAccount()
  if (!account) return ''
  try {
    const response = await client.acquireTokenSilent({ account, scopes: [config.api_scope] })
    return response.accessToken
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) return ''
    throw error
  }
}

export async function signInWithMicrosoft() {
  const config = await loadAuthConfig()
  const client = await entraClient(config)
  if (!client) throw new Error('Microsoft Entra sign-in is not enabled for this deployment')
  const response = await client.loginPopup({ scopes: [config.api_scope] })
  if (response.account) client.setActiveAccount(response.account)
  if (!response.accessToken) throw new Error('Microsoft Entra did not return an API access token')
  return response.accessToken
}

export async function signOutMicrosoft() {
  const config = await loadAuthConfig()
  if (config.mode !== 'entra') return
  const client = await entraClient(config)
  const account = client.getActiveAccount()
  if (account) await client.logoutPopup({ account, postLogoutRedirectUri: window.location.origin })
}
