// Configuracao Firebase Authentication (Projeto: antigravityvmoracle)
// Provedor unico: Google Sign-In com restricao Zero-Trust para williamdevide@gmail.com
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyCtq4EegydU9AE2OGrNkiXWSyEs_-dznu8",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "antigravityvmoracle.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "antigravityvmoracle",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "antigravityvmoracle.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "35864765274",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:35864765274:web:694462c4e6c9a4ccdf0963",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: 'select_account',
});

export const ALLOWED_ADMIN_EMAIL = (
  import.meta.env.VITE_ALLOWED_ADMIN_EMAIL || 'williamdevide@gmail.com'
)
  .trim()
  .toLowerCase();

export const ALLOWED_EMAIL = ALLOWED_ADMIN_EMAIL;

export async function loginWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider);
  const email = (result.user?.email || '').trim().toLowerCase();
  if (email !== ALLOWED_ADMIN_EMAIL) {
    await signOut(auth);
    throw new Error(`Acesso negado: a conta ${email} não está autorizada. Use ${ALLOWED_ADMIN_EMAIL}.`);
  }
  return result.user;
}

export async function logoutGoogle() {
  await signOut(auth);
}
