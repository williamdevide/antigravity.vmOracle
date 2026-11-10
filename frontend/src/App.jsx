import React, { useState, useEffect, useCallback } from 'react';
import {
  Server, Cpu, HardDrive, Activity, Play, Square, RefreshCw,
  Terminal, ShieldCheck, AlertTriangle, CheckCircle2, Clock, Zap,
  Globe, Plus, Trash2, ExternalLink, Code2, Rocket, FolderGit2,
  Github, Search, Lock, LogOut, UserCheck, Edit3, Check, X,
  Database, Layers, Settings, FileText, GitCommit, GitBranch,
  Key, Copy, ArrowLeft, Sparkles, Eye, EyeOff, RotateCcw, Box,
  ChevronRight, ArrowUpRight, Save, Folder, Table, FileCode, ChevronDown,
  Sun, Moon
} from 'lucide-react';
import { auth, loginWithGoogle, logoutGoogle, ALLOWED_EMAIL } from './firebase';
import { onAuthStateChanged } from 'firebase/auth';

export default function App() {
  // Autenticação Firebase (Zero-Trust Google)
  const [user, setUser] = useState(null);
  const [idToken, setIdToken] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Navegação da Sidebar: 'projects' | 'databases' | 'overview' | 'hunter'
  const [activeNav, setActiveNav] = useState('projects');

  // Dados Globais do A.C.O. v3.0
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);

  // Modal de Gerenciamento do Projeto (Overlay Modal)
  const [activeProjectSlug, setActiveProjectSlug] = useState(null);
  // 'controls' | 'env' | 'deployments' | 'logs'
  const [projectTab, setProjectTab] = useState('controls');
  const [projectLogs, setProjectLogs] = useState('');
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [expandedDeployId, setExpandedDeployId] = useState(null);

  // Edição do Projeto no Modal
  const [envEditorText, setEnvEditorText] = useState('');
  const [settingsBranch, setSettingsBranch] = useState('main');
  const [settingsStartCmd, setSettingsStartCmd] = useState('');
  const [settingsAutoDeploy, setSettingsAutoDeploy] = useState(true);
  const [injectDbSlug, setInjectDbSlug] = useState('');

  // Tema da Interface: 'dark' | 'light'
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('aco_theme') || 'dark';
  });

  useEffect(() => {
    localStorage.setItem('aco_theme', theme);
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.remove('dark');
      root.classList.add('light');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Formatador de Data/Hora no Timezone Oficial do Brasil (America/Sao_Paulo / UTC-3)
  const formatDateTimeBR = (isoOrDate) => {
    if (!isoOrDate) return '-';
    try {
      const d = new Date(isoOrDate);
      if (isNaN(d.getTime())) {
        return String(isoOrDate);
      }
      return d.toLocaleString('pt-BR', {
        timeZone: 'America/Sao_Paulo',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch (e) {
      return String(isoOrDate);
    }
  };

  // Renomear URL HTTPS
  const [newSlugValue, setNewSlugValue] = useState('');
  const [newCustomDomainValue, setNewCustomDomainValue] = useState('');

  // Modal de Criação de Novo Projeto (Overlay Modal)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [deployForm, setDeployForm] = useState({
    name: '',
    slug: '',
    customDomain: '',
    gitUrl: '',
    projectType: 'auto',
    branch: 'main',
    startCommand: '',
    envVarsText: '',
    autoDeploy: true,
    gitToken: '',
    cronSchedule: '',
    cronCommand: '',
    createDatabase: false,
    databaseEngine: 'mariadb',
    initialSqlFile: '',
    initialSql: ''
  });
  const [slugManuallyEdited, setSlugManuallyEdited] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState(null);

  // Banco de Dados no Card do Projeto (Aba 'database')
  const [projectSqlScript, setProjectSqlScript] = useState('');
  const [projectSqlFilePath, setProjectSqlFilePath] = useState('');
  const [executingProjectSql, setExecutingProjectSql] = useState(false);
  const [projectSqlFeedback, setProjectSqlFeedback] = useState(null);
  const [newProjectDbEngine, setNewProjectDbEngine] = useState('mariadb');
  const [creatingProjectDb, setCreatingProjectDb] = useState(false);

  // Cron State
  const [projectCron, setProjectCron] = useState({ enabled: false, schedule: '* * * * *', command: '', recentLogs: '' });
  const [loadingCron, setLoadingCron] = useState(false);
  const [savingCron, setSavingCron] = useState(false);
  const [runningCron, setRunningCron] = useState(false);
  const [cronMsg, setCronMsg] = useState(null);

  // File Tree Explorer
  const [filesPath, setFilesPath] = useState('');
  const [filesList, setFilesList] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loadingFileContent, setLoadingFileContent] = useState(false);

  // Database Explorer (Estrutura e Dados)
  const [selectedDbName, setSelectedDbName] = useState('labw');
  const [dbTables, setDbTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState('vaga');
  const [tableSchema, setTableSchema] = useState([]);
  const [tableData, setTableData] = useState({ columns: [], rows: [], total: 0 });
  const [dbExplorerTab, setDbExplorerTab] = useState('data'); // 'data' | 'schema'
  const [loadingDbExplorer, setLoadingDbExplorer] = useState(false);

  // GitHub Repos
  const [ghRepos, setGhRepos] = useState([]);
  const [ghUser, setGhUser] = useState('WilliamDevide');
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoSearch, setRepoSearch] = useState('');
  const [selectedRepoInfo, setSelectedRepoInfo] = useState(null);

  // Bancos de Dados 1-Clique
  const [dbForm, setDbForm] = useState({
    name: '',
    engine: 'sqlite'
  });
  const [creatingDb, setCreatingDb] = useState(false);
  const [dbInjectTargetProject, setDbInjectTargetProject] = useState({});

  const showToastMsg = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 5000);
  };

  // Monitora sessão do Firebase Auth
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        if (currentUser.email?.toLowerCase() !== ALLOWED_EMAIL.toLowerCase()) {
          await logoutGoogle();
          setUser(null);
          setIdToken(null);
          setAuthError(`Acesso bloqueado: A conta ${currentUser.email} não tem permissão.`);
        } else {
          const token = await currentUser.getIdToken();
          setUser(currentUser);
          setIdToken(token);
          setAuthError(null);
        }
      } else {
        setUser(null);
        setIdToken(null);
      }
      setAuthLoading(false);
    });
    return () => unsubscribe();
  }, []);

  // Helper de requisição autenticada
  const authFetch = useCallback(async (url, options = {}) => {
    const currentToken = auth.currentUser ? await auth.currentUser.getIdToken() : idToken;
    const headers = {
      ...(options.headers || {}),
      'Authorization': `Bearer ${currentToken}`
    };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401 || res.status === 403) {
      throw new Error('Sessão expirada. Faça login novamente.');
    }
    return res;
  }, [idToken]);

  const fetchOverview = useCallback(async () => {
    if (!user) return;
    try {
      setLoading(true);
      const res = await authFetch('/api/overview');
      if (!res.ok) {
        const errorText = await res.text().catch(() => '');
        throw new Error(`Falha ao comunicar com a VM (HTTP ${res.status}): ${errorText || res.statusText}`);
      }
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user, authFetch]);

  const fetchGithubRepos = useCallback(async (username = ghUser) => {
    if (!user) return;
    try {
      setLoadingRepos(true);
      const res = await authFetch(`/api/github/repos?username=${encodeURIComponent(username)}`);
      const json = await res.json();
      if (json.status === 'success' || Array.isArray(json.repos)) {
        setGhRepos(json.repos || []);
      }
    } catch (err) {
      console.error('Erro ao buscar repositórios:', err);
    } finally {
      setLoadingRepos(false);
    }
  }, [user, ghUser, authFetch]);

  useEffect(() => {
    if (user) {
      fetchOverview();
      fetchGithubRepos('WilliamDevide');
      const interval = setInterval(fetchOverview, 10000);
      return () => clearInterval(interval);
    }
  }, [user, fetchOverview, fetchGithubRepos]);

  const activeProject = (data?.projects || []).find(p => p.slug === activeProjectSlug) || null;

  useEffect(() => {
    if (activeProject) {
      setEnvEditorText(activeProject.envVarsText || '');
      setSettingsBranch(activeProject.branch || 'main');
      setSettingsStartCmd(activeProject.startCommand || '');
      setSettingsAutoDeploy(activeProject.autoDeploy !== false);
      setNewSlugValue(activeProject.slug || '');
      setNewCustomDomainValue(activeProject.customDomain || '');
      if (activeProject.deploymentsHistory?.length > 0) {
        setExpandedDeployId(activeProject.deploymentsHistory[0].id);
      }
    }
  }, [activeProjectSlug, activeProject?.slug]);

  const fetchProjectRuntimeLogs = async (slug) => {
    if (!slug) return;
    try {
      setLoadingLogs(true);
      const res = await authFetch(`/api/projects/${slug}/logs?lines=120`);
      const json = await res.json();
      setProjectLogs(json.logs || json.runtimeLogs || 'Nenhum log disponível.');
    } catch (err) {
      setProjectLogs(`Erro ao carregar logs: ${err.message}`);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    if (activeProjectSlug && projectTab === 'logs') {
      fetchProjectRuntimeLogs(activeProjectSlug);
    }
  }, [activeProjectSlug, projectTab]);

  const fetchProjectCron = useCallback(async (slug) => {
    if (!slug) return;
    try {
      setLoadingCron(true);
      const res = await authFetch(`/api/projects/${slug}/cron`);
      const json = await res.json();
      if (json.cron) {
        setProjectCron(json.cron);
      }
    } catch (err) {
      console.error('Erro ao buscar cron:', err);
    } finally {
      setLoadingCron(false);
    }
  }, [authFetch]);

  useEffect(() => {
    if (activeProjectSlug && projectTab === 'cron') {
      fetchProjectCron(activeProjectSlug);
    }
  }, [activeProjectSlug, projectTab, fetchProjectCron]);

  // Busca real do arquivo .env no disco
  const fetchProjectRealEnv = useCallback(async (slug) => {
    if (!slug) return;
    try {
      const res = await authFetch(`/api/projects/${slug}/env`);
      const json = await res.json();
      if (json.envText) {
        setEnvEditorText(json.envText);
      }
    } catch (err) {
      console.error('Erro ao buscar .env do disco:', err);
    }
  }, [authFetch]);

  useEffect(() => {
    if (activeProjectSlug && projectTab === 'env') {
      fetchProjectRealEnv(activeProjectSlug);
    }
  }, [activeProjectSlug, projectTab, fetchProjectRealEnv]);

  // Explorador de Arquivos do Projeto (File Tree)
  const fetchProjectFiles = useCallback(async (slug, path = '') => {
    if (!slug) return;
    try {
      setLoadingFiles(true);
      const res = await authFetch(`/api/projects/${slug}/files?path=${encodeURIComponent(path)}`);
      const json = await res.json();
      setFilesList(json.items || []);
      setFilesPath(json.currentPath || '');
    } catch (err) {
      console.error('Erro ao listar arquivos:', err);
    } finally {
      setLoadingFiles(false);
    }
  }, [authFetch]);

  const fetchFileContent = useCallback(async (slug, filePath) => {
    if (!slug || !filePath) return;
    try {
      setLoadingFileContent(true);
      const res = await authFetch(`/api/projects/${slug}/file-content?path=${encodeURIComponent(filePath)}`);
      const json = await res.json();
      setSelectedFile(json);
    } catch (err) {
      console.error('Erro ao ler conteudo do arquivo:', err);
    } finally {
      setLoadingFileContent(false);
    }
  }, [authFetch]);

  useEffect(() => {
    if (activeProjectSlug && projectTab === 'files') {
      fetchProjectFiles(activeProjectSlug, filesPath);
    }
  }, [activeProjectSlug, projectTab, filesPath, fetchProjectFiles]);

  // Explorador de Banco de Dados (Estrutura e Dados)
  const fetchDbTables = useCallback(async (dbName = 'labw') => {
    try {
      setLoadingDbExplorer(true);
      const res = await authFetch(`/api/databases/explorer/tables?db=${encodeURIComponent(dbName)}`);
      const json = await res.json();
      const tbls = json.tables || [];
      setDbTables(tbls);
      if (tbls.length > 0 && (!selectedTable || !tbls.some(t => t.name === selectedTable))) {
        setSelectedTable(tbls[0].name);
      }
    } catch (err) {
      console.error('Erro ao buscar tabelas do banco:', err);
    } finally {
      setLoadingDbExplorer(false);
    }
  }, [authFetch, selectedTable]);

  const fetchTableDetails = useCallback(async (dbName = 'labw', tableName = '') => {
    if (!tableName) return;
    try {
      setLoadingDbExplorer(true);
      const [resSchema, resData] = await Promise.all([
        authFetch(`/api/databases/explorer/schema?db=${encodeURIComponent(dbName)}&table=${encodeURIComponent(tableName)}`),
        authFetch(`/api/databases/explorer/data?db=${encodeURIComponent(dbName)}&table=${encodeURIComponent(tableName)}&limit=50&offset=0`)
      ]);
      const jsonSchema = await resSchema.json();
      const jsonData = await resData.json();
      setTableSchema(jsonSchema.schema || []);
      setTableData({
        columns: jsonData.columns || [],
        rows: jsonData.rows || [],
        total: jsonData.total || 0
      });
    } catch (err) {
      console.error('Erro ao buscar dados da tabela:', err);
    } finally {
      setLoadingDbExplorer(false);
    }
  }, [authFetch]);

  useEffect(() => {
    if (activeNav === 'databases') {
      fetchDbTables(selectedDbName);
    }
  }, [activeNav, selectedDbName, fetchDbTables]);

  useEffect(() => {
    if (activeNav === 'databases' && selectedTable) {
      fetchTableDetails(selectedDbName, selectedTable);
    }
  }, [activeNav, selectedDbName, selectedTable, fetchTableDetails]);

  const handleSaveCron = async () => {
    if (!activeProjectSlug) return;
    try {
      setSavingCron(true);
      setCronMsg(null);
      const res = await authFetch(`/api/projects/${activeProjectSlug}/cron`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          schedule: projectCron.schedule,
          command: projectCron.command,
          enabled: projectCron.enabled
        })
      });
      const json = await res.json();
      if (json.cron) {
        setProjectCron(json.cron);
        setCronMsg({ type: 'success', text: 'Agendamento Cron atualizado com sucesso!' });
        showToastMsg('Configuração Cron salva!');
      } else {
        throw new Error(json.message || 'Erro ao salvar cron');
      }
    } catch (err) {
      setCronMsg({ type: 'error', text: err.message });
      showToastMsg(err.message, 'error');
    } finally {
      setSavingCron(false);
    }
  };

  const handleRunCronNow = async () => {
    if (!activeProjectSlug) return;
    try {
      setRunningCron(true);
      setCronMsg(null);
      const res = await authFetch(`/api/projects/${activeProjectSlug}/cron/run-now`, {
        method: 'POST'
      });
      const json = await res.json();
      if (json.ok) {
        setCronMsg({ type: 'success', text: 'Tarefa Cron executada com sucesso!' });
        showToastMsg('Execução Cron manual concluída!');
        if (json.cron) setProjectCron(json.cron);
      } else {
        throw new Error(json.message || 'Falha ao executar');
      }
    } catch (err) {
      setCronMsg({ type: 'error', text: err.message });
      showToastMsg(err.message, 'error');
    } finally {
      setRunningCron(false);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      setAuthError(null);
      setAuthLoading(true);
      await loginWithGoogle();
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    await logoutGoogle();
    setData(null);
  };

  const sanitizeSlug = (val) => {
    return val.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
  };

  // Estimativa de tamanho em disco pós-build com rótulos concisos
  const getDiskEstimate = (sizeKb, language, pType = 'auto') => {
    const repoMb = Math.max((sizeKb || 0) / 1024, 0.1);
    const lang = (language || '').toLowerCase();
    let buildMb = repoMb * 1.5;
    let label = 'Estático';

    if (pType === 'fullstack') {
      buildMb = repoMb + 85;
      label = 'Full-Stack';
    } else if (lang === 'python' || pType === 'python') {
      buildMb = repoMb + 65;
      label = 'Python .venv';
    } else if (['javascript', 'typescript', 'vue', 'svelte'].includes(lang) || pType === 'react-vite') {
      buildMb = repoMb + 12;
      label = 'Vite Otimizado';
    } else if (pType === 'node') {
      buildMb = repoMb + 55;
      label = 'Node.js API';
    }

    const formatSize = (mb) => mb < 1 ? `${Math.round(mb * 1024)} KB` : `${mb.toFixed(1)} MB`;
    return {
      repoFormatted: formatSize(repoMb),
      diskFormatted: formatSize(buildMb),
      label
    };
  };

  const selectRepository = (repo) => {
    let detectedType = 'auto';
    const lang = (repo.language || '').toLowerCase();
    if (lang === 'python') detectedType = 'python';
    else if (lang === 'html' || lang === 'css') detectedType = 'static';
    else if (lang === 'javascript' || lang === 'typescript') detectedType = 'auto';

    const defaultSlug = sanitizeSlug(repo.name);
    setDeployForm({
      ...deployForm,
      name: repo.name,
      slug: defaultSlug,
      gitUrl: repo.clone_url || repo.cloneUrl,
      branch: repo.default_branch || repo.defaultBranch || 'main',
      projectType: detectedType
    });
    setSlugManuallyEdited(false);
    setSelectedRepoInfo(repo);
    setDeployResult(null);
  };

  const handleDeployProject = async (e) => {
    e.preventDefault();
    if (!deployForm.name) return;
    try {
      setDeploying(true);
      setDeployResult(null);
      const res = await authFetch('/api/projects/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...deployForm,
          trigger: 'manual'
        })
      });
      const json = await res.json();
      setDeployResult(json);
      if (json.status === 'success' || json.ok) {
        showToastMsg(`Deploy de "${deployForm.name}" concluído!`);
        await fetchOverview();
      } else {
        showToastMsg(json.message || 'Erro durante o deploy', 'error');
      }
    } catch (err) {
      setDeployResult({ status: 'error', message: err.message, log: err.message });
      showToastMsg(err.message, 'error');
    } finally {
      setDeploying(false);
    }
  };

  const handleManualRedeploy = async (proj) => {
    try {
      setActionLoading(true);
      showToastMsg(`Iniciando Deploy de "${proj.name}"...`);
      const res = await authFetch('/api/projects/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: proj.name,
          slug: proj.slug,
          customDomain: proj.customDomain || '',
          gitUrl: proj.gitUrl || proj.repoUrl || '',
          projectType: proj.projectType || 'auto',
          branch: proj.branch || 'main',
          startCommand: proj.startCommand || '',
          envVarsText: proj.envVarsText || '',
          autoDeploy: proj.autoDeploy !== false,
          trigger: 'manual'
        })
      });
      const json = await res.json();
      if (json.status === 'success' || json.ok) {
        showToastMsg(`Deploy de "${proj.name}" atualizado!`);
      } else {
        showToastMsg(`Falha no deploy: ${json.message}`, 'error');
      }
      await fetchOverview();
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCheckGithubUpdatesNow = async () => {
    try {
      setActionLoading(true);
      showToastMsg('Verificando commits no GitHub...');
      const res = await authFetch('/api/projects/check-updates', { method: 'POST' });
      const json = await res.json();
      const updated = (json.results || json.triggered || []).filter(r => r.updated || r.status === 'SUCCESS');
      if (updated.length > 0) {
        showToastMsg(`${updated.length} projeto(s) atualizado(s) e reimplantado(s)!`);
      } else {
        showToastMsg('Projetos já sincronizados com o último commit do GitHub.');
      }
      await fetchOverview();
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleServiceControl = async (slug, action) => {
    try {
      setActionLoading(true);
      const res = await authFetch(`/api/projects/${slug}/service`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      const json = await res.json();
      if (json.status === 'success' || json.ok) {
        showToastMsg(`Serviço ${action === 'restart' ? 'reiniciado' : action === 'start' ? 'iniciado' : 'parado'}!`);
      } else {
        showToastMsg(json.message || 'Erro ao controlar serviço', 'error');
      }
      await fetchOverview();
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveProjectSettings = async (slug, redeploy = false) => {
    try {
      setActionLoading(true);
      const res = await authFetch(`/api/projects/${slug}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          envVarsText: envEditorText,
          autoDeploy: settingsAutoDeploy,
          branch: settingsBranch,
          startCommand: settingsStartCmd,
          redeploy
        })
      });
      const json = await res.json();
      if (json.status === 'success' || json.ok) {
        showToastMsg(redeploy ? 'Configurações salvas e projeto recompilado!' : 'Configurações e .env salvos!');
      } else {
        showToastMsg(json.message || 'Erro ao salvar', 'error');
      }
      await fetchOverview();
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRenameProject = async (oldSlug) => {
    if (!newSlugValue) return;
    try {
      setActionLoading(true);
      const res = await authFetch(`/api/projects/${oldSlug}/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          newSlug: newSlugValue,
          customDomain: newCustomDomainValue
        })
      });
      const json = await res.json();
      if (json.status === 'success' || json.ok) {
        showToastMsg(`Endereço HTTPS atualizado com sucesso!`);
        if (activeProjectSlug === oldSlug) {
          setActiveProjectSlug(newSlugValue);
        }
        await fetchOverview();
      } else {
        showToastMsg(json.message || 'Erro ao alterar HTTPS', 'error');
      }
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteProject = async (slug) => {
    if (!window.confirm(`Tem certeza que deseja excluir "${slug}" e liberar disco/HTTPS?`)) return;
    try {
      setActionLoading(true);
      await authFetch(`/api/projects/${slug}`, { method: 'DELETE' });
      showToastMsg(`Projeto "${slug}" removido.`);
      if (activeProjectSlug === slug) {
        setActiveProjectSlug(null);
      }
      await fetchOverview();
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Bancos de Dados 1-Clique
  const handleCreateDatabase = async (e) => {
    e.preventDefault();
    if (!dbForm.name) return;
    try {
      setCreatingDb(true);
      const res = await authFetch('/api/databases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dbForm)
      });
      const json = await res.json();
      if (json.status === 'success' || json.ok) {
        showToastMsg(`Banco "${dbForm.name}" provisionado com sucesso!`);
        setDbForm({ name: '', engine: 'sqlite' });
        await fetchOverview();
      } else {
        showToastMsg(json.message || 'Erro ao criar banco', 'error');
      }
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setCreatingDb(false);
    }
  };

  const handleDeleteDatabase = async (dbSlug) => {
    if (!window.confirm(`Deseja apagar o banco "${dbSlug}" e todos os dados?`)) return;
    try {
      setActionLoading(true);
      await authFetch(`/api/databases/${dbSlug}`, { method: 'DELETE' });
      showToastMsg(`Banco "${dbSlug}" excluído.`);
      await fetchOverview();
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleInjectDatabaseIntoProject = async (dbSlug, projectSlug) => {
    if (!dbSlug || !projectSlug) return;
    try {
      setActionLoading(true);
      const res = await authFetch(`/api/databases/${dbSlug}/inject/${projectSlug}`, {
        method: 'POST'
      });
      const json = await res.json();
      if (json.status === 'success' || json.ok) {
        showToastMsg(json.message || 'DATABASE_URL injetada no .env!');
        await fetchOverview();
      } else {
        showToastMsg(json.message || 'Falha ao injetar banco', 'error');
      }
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Executar Script SQL diretamente no banco vinculado ao projeto
  const handleExecuteProjectSql = async (dbSlug) => {
    if (!dbSlug) {
      showToastMsg('Nenhum banco de dados selecionado.', 'error');
      return;
    }
    if (!projectSqlScript.trim() && !projectSqlFilePath.trim()) {
      showToastMsg('Informe um script SQL ou o caminho de um arquivo .sql', 'error');
      return;
    }
    try {
      setExecutingProjectSql(true);
      setProjectSqlFeedback(null);
      const res = await authFetch(`/api/databases/${dbSlug}/import-sql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sqlContent: projectSqlScript,
          sqlFilePath: projectSqlFilePath
        })
      });
      const json = await res.json();
      if (json.status === 'success' || json.ok) {
        setProjectSqlFeedback({
          success: true,
          message: json.message || 'Script SQL executado com sucesso!',
          tablesCount: json.tablesCount,
          timeMs: json.timeMs
        });
        showToastMsg('Script SQL executado com sucesso!');
        await fetchOverview();
      } else {
        setProjectSqlFeedback({
          success: false,
          message: json.message || 'Erro ao executar script SQL'
        });
        showToastMsg(json.message || 'Erro ao executar SQL', 'error');
      }
    } catch (err) {
      setProjectSqlFeedback({
        success: false,
        message: err.message
      });
      showToastMsg(err.message, 'error');
    } finally {
      setExecutingProjectSql(false);
    }
  };

  // Criar e vincular banco ao projeto em 1-Clique (com injeção automática no .env)
  const handleCreateAndInjectProjectDb = async (projectSlug) => {
    if (!projectSlug) return;
    try {
      setCreatingProjectDb(true);
      setProjectSqlFeedback(null);
      const res = await authFetch(`/api/projects/${projectSlug}/database/create-and-inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          engine: newProjectDbEngine,
          initialSql: projectSqlScript,
          initialSqlFile: projectSqlFilePath
        })
      });
      const json = await res.json();
      if (json.status === 'success' || json.ok) {
        showToastMsg(`Banco de dados provisionado e injetado no .env!`);
        await fetchOverview();
        if (projectTab === 'env') {
          await fetchProjectRealEnv(projectSlug);
        }
      } else {
        showToastMsg(json.message || 'Falha ao provisionar banco para o projeto', 'error');
      }
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setCreatingProjectDb(false);
    }
  };

  // Caçador ARM
  const handleHunterAction = async (endpoint) => {
    try {
      setActionLoading(true);
      await authFetch(`/api/hunter/${endpoint}`, { method: 'POST' });
      showToastMsg(`Comando enviado ao Caçador ARM!`);
      setTimeout(fetchOverview, 1200);
    } catch (err) {
      showToastMsg(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const copyToClipboard = (text, label = 'Texto') => {
    navigator.clipboard.writeText(text);
    showToastMsg(`${label} copiado!`);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
          <p className="text-sm font-medium">Verificando credenciais Zero-Trust Google...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 text-slate-100">
        <div className="max-w-md w-full bg-slate-900/90 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur">
          <div className="flex flex-col items-center text-center">
            <div className="p-4 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 mb-4">
              <Lock className="w-10 h-10" />
            </div>
            <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mb-2">
              A.C.O. v3.0 • Coolify Edition
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Antigravity Cloud Orchestrator
            </h1>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              PaaS Privado & Orquestrador Full-Stack na Oracle Cloud (`147.15.2.73`). Acesso exclusivo via Google Zero-Trust.
            </p>

            {authError && (
              <div className="mt-5 w-full p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-start gap-2.5 text-left">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span>{authError}</span>
              </div>
            )}

            <button
              onClick={handleGoogleLogin}
              className="mt-6 w-full py-3.5 px-5 rounded-xl bg-white hover:bg-slate-100 text-slate-900 font-semibold text-sm flex items-center justify-center gap-3 shadow-lg transition cursor-pointer"
            >
              <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              <span className="truncate">Entrar com Google ({ALLOWED_EMAIL})</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const vm = data?.vm || {};
  const aco = data?.acoPlatform || {};
  const hunter = data?.hunter || {};
  const projects = data?.projects || [];
  const databases = data?.databases || [];
  const baseDomain = data?.baseDomain || '147.15.2.73.sslip.io';
  const isHunting = hunter?.service_active === 'active';

  const filteredRepos = ghRepos.filter(r =>
    (r.name || '').toLowerCase().includes(repoSearch.toLowerCase()) ||
    (r.description && r.description.toLowerCase().includes(repoSearch.toLowerCase()))
  );

  const selectedEstimate = selectedRepoInfo
    ? getDiskEstimate(selectedRepoInfo.size_kb || selectedRepoInfo.sizeKB, selectedRepoInfo.language, deployForm.projectType)
    : null;

  const totalProjectsRamMb = projects.reduce((acc, p) => acc + (p.ramMb || p.ramMB || 0), 0);
  const totalProjectsDiskMb = projects.reduce((acc, p) => acc + (p.diskMb || p.diskMB || 0), 0);


  // =========================================================================
  // RENDERIZADOR DO PAINEL EXPANSÍVEL DO PROJETO (INLINE ACCORDION NO CORPO)
  // =========================================================================
  const renderProjectDetails = (activeProject) => {
    if (!activeProject) return null;
    return (
      <div className="border-t border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/70 p-4 sm:p-5 space-y-4 animate-in fade-in duration-150">
        {/* Abas de Navegação do Projeto (Textos Concisos & Design Clean) */}
        <div className="flex items-center gap-1.5 pb-2.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 overflow-x-auto">
          <button
            type="button"
            onClick={() => setProjectTab('controls')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
              projectTab === 'controls'
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-600/20 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 font-bold shadow-sm'
                : 'bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
            }`}
          >
            <Settings className="w-3.5 h-3.5 shrink-0" /> Config
          </button>

          <button
            type="button"
            onClick={() => setProjectTab('env')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
              projectTab === 'env'
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-600/20 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 font-bold shadow-sm'
                : 'bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
            }`}
          >
            <Key className="w-3.5 h-3.5 text-amber-500 shrink-0" /> .env
          </button>

          <button
            type="button"
            onClick={() => setProjectTab('deployments')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
              projectTab === 'deployments'
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-600/20 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 font-bold shadow-sm'
                : 'bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
            }`}
          >
            <GitCommit className="w-3.5 h-3.5 text-indigo-500 shrink-0" /> Histórico ({activeProject.deploymentsHistory?.length || 0})
          </button>

          <button
            type="button"
            onClick={() => setProjectTab('logs')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
              projectTab === 'logs'
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-600/20 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 font-bold shadow-sm'
                : 'bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
            }`}
          >
            <Terminal className="w-3.5 h-3.5 text-emerald-500 shrink-0" /> Logs
          </button>

          <button
            type="button"
            onClick={() => setProjectTab('cron')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
              projectTab === 'cron'
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-600/20 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 font-bold shadow-sm'
                : 'bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
            }`}
          >
            <Clock className="w-3.5 h-3.5 text-cyan-500 shrink-0" /> Cron
          </button>

          <button
            type="button"
            onClick={() => setProjectTab('files')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
              projectTab === 'files'
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-600/20 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 font-bold shadow-sm'
                : 'bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
            }`}
          >
            <FolderGit2 className="w-3.5 h-3.5 text-yellow-500 shrink-0" /> Arquivos
          </button>

          <button
            type="button"
            onClick={() => setProjectTab('database')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
              projectTab === 'database'
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-600/20 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 font-bold shadow-sm'
                : 'bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
            }`}
          >
            <Database className="w-3.5 h-3.5 text-indigo-500 shrink-0" /> Banco de Dados
          </button>
        </div>

        {/* Conteúdo das Abas */}
        <div className="space-y-4 pt-1">
              {/* ABA 1: CONFIGURAÇÕES & AÇÕES */}
              {projectTab === 'controls' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Controles de Execução */}
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                      <Play className="w-3.5 h-3.5 shrink-0" /> Controle de Ciclo de Vida
                    </h3>

                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => handleServiceControl(activeProject.slug, 'restart')}
                        disabled={actionLoading}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                      >
                        <RotateCcw className="w-3.5 h-3.5 text-cyan-400 shrink-0" /> Reiniciar
                      </button>

                      {activeProject.status === 'running' ? (
                        <button
                          onClick={() => handleServiceControl(activeProject.slug, 'stop')}
                          disabled={actionLoading}
                          className="px-3 py-1.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-xs text-amber-300 flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                        >
                          <Square className="w-3.5 h-3.5 shrink-0" /> Parar
                        </button>
                      ) : (
                        <button
                          onClick={() => handleServiceControl(activeProject.slug, 'start')}
                          disabled={actionLoading}
                          className="px-3 py-1.5 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-xs text-emerald-300 flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                        >
                          <Play className="w-3.5 h-3.5 shrink-0" /> Iniciar
                        </button>
                      )}

                      <button
                        onClick={() => handleDeleteProject(activeProject.slug)}
                        disabled={actionLoading}
                        className="px-3 py-1.5 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-xs text-red-300 flex items-center gap-1.5 cursor-pointer ml-auto whitespace-nowrap"
                      >
                        <Trash2 className="w-3.5 h-3.5 shrink-0" /> Excluir
                      </button>
                    </div>

                    <div className="pt-3 border-t border-slate-800 space-y-3">
                      <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between whitespace-nowrap">
                        <div>
                          <p className="text-xs font-semibold text-white">Auto-Deploy Contínuo</p>
                          <p className="text-[10px] text-slate-400">Watcher a cada 60s + Webhook</p>
                        </div>
                        <input
                          type="checkbox"
                          checked={settingsAutoDeploy}
                          onChange={(e) => setSettingsAutoDeploy(e.target.checked)}
                          className="w-4 h-4 accent-cyan-500 cursor-pointer"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-2.5">
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Branch</label>
                          <input
                            type="text"
                            value={settingsBranch}
                            onChange={(e) => setSettingsBranch(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white font-mono"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Porta Interna</label>
                          <input
                            type="text"
                            disabled
                            value={activeProject.port ? `127.0.0.1:${activeProject.port}` : 'Caddy Static'}
                            className="w-full bg-slate-900/50 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-400 font-mono"
                          />
                        </div>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                        <div className="flex items-center justify-between text-[11px] whitespace-nowrap">
                          <span className="text-slate-400">Webhook GitHub:</span>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(`https://${baseDomain}/api/webhooks/github/${activeProject.slug}`, 'Webhook')}
                            className="text-cyan-400 hover:underline flex items-center gap-1 cursor-pointer"
                          >
                            <Copy className="w-3 h-3" /> Copiar
                          </button>
                        </div>
                        <p className="text-[10px] font-mono text-slate-300 truncate">
                          https://{baseDomain}/api/webhooks/github/{activeProject.slug}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleSaveProjectSettings(activeProject.slug, false)}
                        disabled={actionLoading}
                        className="w-full py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs cursor-pointer whitespace-nowrap"
                      >
                        Salvar Configurações
                      </button>
                    </div>
                  </div>

                  {/* Domínio & Endereço HTTPS */}
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                      <Globe className="w-3.5 h-3.5 shrink-0" /> Endereço HTTPS & Domínio
                    </h3>

                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Subdomínio (.sslip.io)</label>
                      <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                        <input
                          type="text"
                          value={newSlugValue}
                          onChange={(e) => setNewSlugValue(sanitizeSlug(e.target.value))}
                          className="w-full bg-transparent px-3 py-1.5 text-xs text-cyan-300 font-mono focus:outline-none min-w-0"
                        />
                        <span className="px-2.5 py-1.5 bg-slate-800 text-xs text-slate-400 font-mono border-l border-slate-800 shrink-0 whitespace-nowrap">
                          .{baseDomain}
                        </span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Domínio Próprio (Opcional)</label>
                      <input
                        type="text"
                        placeholder="Ex: app.meudominio.com.br"
                        value={newCustomDomainValue}
                        onChange={(e) => setNewCustomDomainValue(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white font-mono"
                      />
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRenameProject(activeProject.slug)}
                      disabled={actionLoading}
                      className="w-full py-2 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-slate-950 font-bold text-xs cursor-pointer whitespace-nowrap"
                    >
                      Atualizar Endereço HTTPS
                    </button>
                  </div>
                </div>
              )}

              {/* ABA 2: VARIÁVEIS (.ENV) */}
              {projectTab === 'env' && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 sm:p-5 space-y-3.5">
                  <div className="flex flex-wrap items-center justify-between gap-2.5">
                    <div>
                      <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
                        <Key className="w-4 h-4 text-amber-400 shrink-0" /> Variáveis de Ambiente (.env)
                      </h3>
                      <p className="text-[11px] text-slate-400">Injetadas na raiz, em /frontend, /backend e no systemd.</p>
                    </div>

                    {/* Injetar Banco */}
                    <div className="flex items-center gap-1.5">
                      <select
                        value={injectDbSlug}
                        onChange={(e) => setInjectDbSlug(e.target.value)}
                        className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200"
                      >
                        <option value="">Injetar Banco...</option>
                        {databases.map(db => (
                          <option key={db.slug} value={db.slug}>{db.name} ({db.engineLabel})</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        disabled={!injectDbSlug || actionLoading}
                        onClick={() => handleInjectDatabaseIntoProject(injectDbSlug, activeProject.slug)}
                        className="px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold cursor-pointer disabled:opacity-40 whitespace-nowrap"
                      >
                        + Injetar
                      </button>
                    </div>
                  </div>

                  <textarea
                    rows={8}
                    value={envEditorText}
                    onChange={(e) => setEnvEditorText(e.target.value)}
                    placeholder={"NODE_ENV=production\nDATABASE_URL=..."}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs font-mono text-amber-200 focus:outline-none focus:border-cyan-500 leading-relaxed"
                  />

                  <div className="flex flex-wrap items-center justify-end gap-2.5">
                    <button
                      type="button"
                      onClick={() => handleSaveProjectSettings(activeProject.slug, false)}
                      disabled={actionLoading}
                      className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white cursor-pointer whitespace-nowrap"
                    >
                      Salvar Apenas .env
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSaveProjectSettings(activeProject.slug, true)}
                      disabled={actionLoading}
                      className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 text-slate-950 font-bold text-xs flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                    >
                      <Rocket className="w-3.5 h-3.5 shrink-0" /> Salvar .env + Recompilar
                    </button>
                  </div>
                </div>
              )}

              {/* ABA 3: HISTÓRICO DE DEPLOYS */}
              {projectTab === 'deployments' && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 sm:p-5 space-y-3">
                  <div className="flex items-center justify-between whitespace-nowrap">
                    <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
                      <GitCommit className="w-4 h-4 text-indigo-400 shrink-0" /> Histórico de Implantações
                    </h3>
                    <span className="text-xs text-slate-400">
                      {activeProject.deploymentsHistory?.length || 0} deploys
                    </span>
                  </div>

                  {(activeProject.deploymentsHistory || []).length === 0 ? (
                    <p className="text-xs text-slate-500 py-6 text-center">Nenhum deploy registrado ainda.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {activeProject.deploymentsHistory.map((dep) => {
                        const isExpanded = expandedDeployId === dep.id;
                        return (
                          <div key={dep.id} className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
                            <div
                              onClick={() => setExpandedDeployId(isExpanded ? null : dep.id)}
                              className="p-3 flex flex-wrap items-center justify-between gap-2 hover:bg-slate-800/50 transition cursor-pointer"
                            >
                              <div className="flex items-center gap-2 flex-wrap min-w-0">
                                <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase whitespace-nowrap shrink-0 ${
                                  dep.status === 'success'
                                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                    : 'bg-red-500/15 text-red-400 border border-red-500/30'
                                }`}>
                                  {dep.status === 'success' ? 'SUCESSO' : 'FALHOU'}
                                </span>

                                <span className="font-mono text-xs text-cyan-300 font-semibold shrink-0">
                                  #{dep.commitHash || 'local'}
                                </span>

                                <span className="text-xs text-white font-medium truncate max-w-[280px]">
                                  {dep.commitMessage || 'Deploy'}
                                </span>

                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono whitespace-nowrap shrink-0">
                                  {dep.trigger}
                                </span>
                              </div>

                              <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono whitespace-nowrap shrink-0">
                                <span>⏱️ {dep.durationSec || dep.durationSeconds || 1}s</span>
                                <span>📅 {formatDateTimeBR(dep.timestamp)}</span>
                              </div>
                            </div>

                            {isExpanded && (
                              <div className="p-3.5 border-t border-slate-800 bg-black/80 text-[10px] font-mono text-emerald-300 whitespace-pre-wrap max-h-64 overflow-y-auto leading-relaxed">
                                {dep.log || 'Sem log detalhado.'}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* ABA 4: LOGS EM TEMPO REAL */}
              {projectTab === 'logs' && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 sm:p-5 space-y-3">
                  <div className="flex items-center justify-between whitespace-nowrap">
                    <div>
                      <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
                        <Terminal className="w-4 h-4 text-emerald-400 shrink-0" /> Console de Execução (Runtime)
                      </h3>
                      <p className="text-[11px] text-slate-400">Saída padrão de stdout/stderr (systemd / caddy)</p>
                    </div>
                    <button
                      onClick={() => fetchProjectRuntimeLogs(activeProject.slug)}
                      className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-cyan-300 flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 shrink-0 ${loadingLogs ? 'animate-spin' : ''}`} /> Atualizar
                    </button>
                  </div>

                  <div className="p-3.5 rounded-xl bg-black/90 border border-slate-800 font-mono text-[11px] text-slate-200 whitespace-pre-wrap h-72 overflow-y-auto leading-relaxed">
                    {loadingLogs ? 'Carregando logs...' : projectLogs}
                  </div>
                </div>
              )}

              {/* ABA 5: CRON / AGENDAMENTOS */}
              {projectTab === 'cron' && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 sm:p-5 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2.5 pb-3 border-b border-slate-800">
                    <div>
                      <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
                        <Clock className="w-4 h-4 text-cyan-400 shrink-0" /> Agendador de Tarefas Cron
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Rotinas em background (PHP, Bash, scripts) com execução isolada no sistema (/etc/cron.d/aco-{activeProject.slug})
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleRunCronNow}
                        disabled={runningCron || !projectCron.command}
                        className="px-3 py-1.5 rounded-xl bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 text-xs font-semibold flex items-center gap-1.5 cursor-pointer disabled:opacity-50 transition"
                      >
                        <Play className="w-3.5 h-3.5 shrink-0" /> {runningCron ? 'Executando...' : 'Testar Agora'}
                      </button>
                      <button
                        type="button"
                        onClick={handleSaveCron}
                        disabled={savingCron}
                        className="px-3.5 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 cursor-pointer disabled:opacity-50 transition shadow-lg shadow-cyan-500/20"
                      >
                        <Save className="w-3.5 h-3.5 shrink-0" /> {savingCron ? 'Salvando...' : 'Salvar Agendamento'}
                      </button>
                    </div>
                  </div>

                  {cronMsg && (
                    <div className={`p-2.5 rounded-xl text-xs flex items-center gap-2 ${
                      cronMsg.type === 'success' ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300' : 'bg-red-500/15 border border-red-500/30 text-red-300'
                    }`}>
                      {cronMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
                      <span>{cronMsg.text}</span>
                    </div>
                  )}

                  {/* Configurações de Cron */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                    <div className="md:col-span-5 space-y-3 bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold text-slate-300">Status do Agendador</label>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={projectCron.enabled}
                            onChange={(e) => setProjectCron({ ...projectCron, enabled: e.target.checked })}
                            className="sr-only peer"
                          />
                          <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500"></div>
                          <span className="ml-2 text-xs font-medium text-slate-400">
                            {projectCron.enabled ? 'Ativo' : 'Pausado'}
                          </span>
                        </label>
                      </div>

                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Expressão Crontab</label>
                        <input
                          type="text"
                          value={projectCron.schedule}
                          onChange={(e) => setProjectCron({ ...projectCron, schedule: e.target.value })}
                          placeholder="* * * * *"
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-500"
                        />
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          <button
                            type="button"
                            onClick={() => setProjectCron({ ...projectCron, schedule: '* * * * *' })}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono"
                          >
                            1 min (* * * * *)
                          </button>
                          <button
                            type="button"
                            onClick={() => setProjectCron({ ...projectCron, schedule: '*/5 * * * *' })}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono"
                          >
                            5 min (*/5 * * * *)
                          </button>
                          <button
                            type="button"
                            onClick={() => setProjectCron({ ...projectCron, schedule: '0 * * * *' })}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono"
                          >
                            1 hora (0 * * * *)
                          </button>
                          <button
                            type="button"
                            onClick={() => setProjectCron({ ...projectCron, schedule: '0 0 * * *' })}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono"
                          >
                            Diário (0 0 * * *)
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Comando a Executar</label>
                        <input
                          type="text"
                          value={projectCron.command}
                          onChange={(e) => setProjectCron({ ...projectCron, command: e.target.value })}
                          placeholder="php cron.php ou php artisan schedule:run"
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
                        />
                        <p className="text-[10px] text-slate-500 mt-1">
                          Executado no diretório: <span className="font-mono text-slate-400">{activeProject.workDir}</span>
                        </p>
                      </div>
                    </div>

                    {/* Visualizador de Logs do Cron */}
                    <div className="md:col-span-7 bg-slate-950 border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-2">
                          <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                            <Terminal className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> Log de Execuções Recentes
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">/var/log/aco-cron/{activeProject.slug}.log</span>
                        </div>
                        <pre className="bg-slate-900/90 text-emerald-400 font-mono text-[11px] p-2.5 rounded-lg overflow-x-auto max-h-56 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                          {loadingCron ? 'Carregando logs do cron...' : projectCron.recentLogs || 'Sem registros de execução ainda.'}
                        </pre>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ABA 6: ÁRVORE DE ARQUIVOS (FILE TREE EXPLORER) */}
              {projectTab === 'files' && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 sm:p-5 space-y-4">
                  {/* Barra de Navegação do Caminho */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2 min-w-0">
                      <FolderGit2 className="w-4 h-4 text-yellow-400 shrink-0" />
                      <span className="text-xs font-bold text-white">Navegador de Arquivos:</span>
                      <div className="flex items-center gap-1 font-mono text-xs text-cyan-300 bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-800 truncate">
                        <button
                          type="button"
                          onClick={() => { setFilesPath(''); setSelectedFile(null); }}
                          className="hover:text-white hover:underline cursor-pointer"
                        >
                          /{activeProject.slug}
                        </button>
                        {filesPath && (
                          <>
                            <span className="text-slate-500">/</span>
                            <span className="text-amber-300 truncate">{filesPath}</span>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {filesPath && (
                        <button
                          type="button"
                          onClick={() => {
                            const parts = filesPath.split('/');
                            parts.pop();
                            setFilesPath(parts.join('/'));
                            setSelectedFile(null);
                          }}
                          className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 flex items-center gap-1 cursor-pointer"
                        >
                          <ArrowLeft className="w-3.5 h-3.5" /> Subir Pasta (..)
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => fetchProjectFiles(activeProject.slug, filesPath)}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
                        title="Atualizar pasta"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${loadingFiles ? 'animate-spin text-cyan-400' : ''}`} />
                      </button>
                    </div>
                  </div>

                  {/* Grid: Lista de Arquivos à Esquerda + Pré-visualização à Direita */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    {/* Lista de Pastas e Arquivos */}
                    <div className="lg:col-span-5 bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-96">
                      <div className="p-2.5 bg-slate-950/60 border-b border-slate-800 text-[11px] font-semibold text-slate-400 flex items-center justify-between">
                        <span>Nome</span>
                        <span>Tamanho</span>
                      </div>
                      <div className="p-1 overflow-y-auto flex-1 space-y-0.5">
                        {loadingFiles ? (
                          <div className="p-8 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
                            <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                            <span>Lendo diretório...</span>
                          </div>
                        ) : filesList.length === 0 ? (
                          <div className="p-8 text-center text-xs text-slate-500">Esta pasta está vazia.</div>
                        ) : (
                          filesList.map((item) => (
                            <button
                              key={item.relativePath}
                              type="button"
                              onClick={() => {
                                if (item.isDirectory) {
                                  setFilesPath(item.relativePath);
                                  setSelectedFile(null);
                                } else {
                                  fetchFileContent(activeProject.slug, item.relativePath);
                                }
                              }}
                              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition cursor-pointer text-left ${
                                selectedFile?.relativePath === item.relativePath
                                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30'
                                  : 'hover:bg-slate-800/80 text-slate-300'
                              }`}
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                {item.isDirectory ? (
                                  <Folder className="w-3.5 h-3.5 text-yellow-400 shrink-0 fill-yellow-400/20" />
                                ) : item.extension === 'php' ? (
                                  <FileCode className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                                ) : item.name.startsWith('.env') ? (
                                  <Key className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                                ) : (
                                  <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                )}
                                <span className="truncate">{item.name}</span>
                              </div>
                              <span className="font-mono text-[10px] text-slate-500 shrink-0 ml-2">
                                {item.sizeFormatted}
                              </span>
                            </button>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Visualizador de Conteúdo do Arquivo */}
                    <div className="lg:col-span-7 bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-96">
                      <div className="p-2.5 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2 min-w-0">
                          <Code2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span className="font-mono text-slate-300 truncate font-semibold">
                            {selectedFile ? selectedFile.relativePath : 'Nenhum arquivo selecionado'}
                          </span>
                          {selectedFile && (
                            <span className="text-[10px] text-slate-500 font-mono">({selectedFile.sizeFormatted})</span>
                          )}
                        </div>
                        {selectedFile?.content && (
                          <button
                            type="button"
                            onClick={() => copyToClipboard(selectedFile.content, selectedFile.relativePath)}
                            className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-cyan-300 flex items-center gap-1 cursor-pointer shrink-0"
                          >
                            <Copy className="w-3 h-3" /> Copiar
                          </button>
                        )}
                      </div>

                      <div className="p-3 overflow-y-auto flex-1 font-mono text-xs bg-slate-950 leading-relaxed">
                        {loadingFileContent ? (
                          <div className="h-full flex items-center justify-center text-slate-400 gap-2">
                            <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                            <span>Carregando arquivo...</span>
                          </div>
                        ) : selectedFile ? (
                          <pre className="text-slate-200 whitespace-pre-wrap selection:bg-cyan-500/30">
                            {selectedFile.content}
                          </pre>
                        ) : (
                          <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-1.5">
                            <FileText className="w-6 h-6 stroke-1 text-slate-600" />
                            <p className="text-xs">Selecione um arquivo à esquerda para visualizar seu código.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ABA 7: BANCO DE DADOS 1-CLIQUE DO PROJETO */}
              {projectTab === 'database' && (() => {
                const boundDb = databases.find(d => 
                  (activeProject.databaseSlug && (d.slug === activeProject.databaseSlug || d.dbName === activeProject.databaseSlug)) ||
                  (activeProject.database_slug && (d.slug === activeProject.database_slug || d.dbName === activeProject.database_slug)) ||
                  d.projectSlug === activeProject.slug ||
                  d.project_slug === activeProject.slug ||
                  d.slug === activeProject.slug ||
                  d.dbName === activeProject.slug ||
                  (activeProject.slug === 'labwarenext' && (d.slug === 'labw' || d.dbName === 'labw')) ||
                  (d.dbName && activeProject.slug && activeProject.slug.toLowerCase().includes(d.dbName.toLowerCase())) ||
                  (d.slug && activeProject.slug && activeProject.slug.toLowerCase().includes(d.slug.toLowerCase()))
                );

                return (
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 sm:p-5 space-y-4">
                    {boundDb ? (
                      <div className="space-y-4">
                        {/* Header do Banco Vinculado */}
                        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
                          <div className="flex items-center gap-3">
                            <div className="p-2.5 rounded-xl bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
                              <Database className="w-5 h-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h3 className="text-sm font-bold text-white">{boundDb.name}</h3>
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                                  {boundDb.engineLabel || boundDb.engine}
                                </span>
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                                  <CheckCircle2 className="w-3 h-3" /> Conectado ao .env
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-400 mt-0.5">
                                Host: <span className="font-mono text-slate-300">{boundDb.host}</span> • Porta: <span className="font-mono text-slate-300">{boundDb.port}</span> • Banco: <span className="font-mono text-indigo-300">{boundDb.database}</span>
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedDbName(boundDb.name || boundDb.slug);
                                setActiveNav('databases');
                              }}
                              className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 flex items-center gap-1.5 transition cursor-pointer"
                            >
                              <Table className="w-3.5 h-3.5 text-indigo-500" /> Explorar Tabelas
                            </button>
                          </div>
                        </div>

                        {/* String de Conexão */}
                        <div className="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-1.5 shadow-sm">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-600 dark:text-slate-400 font-medium flex items-center gap-1.5">
                              <Key className="w-3.5 h-3.5 text-amber-500" /> Variável DATABASE_URL (.env)
                            </span>
                            <button
                              type="button"
                              onClick={() => copyToClipboard(boundDb.connectionSnippet || boundDb.databaseUrl, 'DATABASE_URL')}
                              className="text-blue-600 dark:text-cyan-400 hover:underline text-xs font-medium flex items-center gap-1 cursor-pointer"
                            >
                              <Copy className="w-3.5 h-3.5" /> Copiar String de Conexão
                            </button>
                          </div>
                          <div className="p-2.5 bg-slate-900 text-amber-300 rounded-lg font-mono text-xs border border-slate-800 break-all select-all">
                            {boundDb.connectionSnippet || boundDb.databaseUrl}
                          </div>
                        </div>

                        {/* Importar e Executar Script SQL (.sql) */}
                        <div className="p-4 bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl space-y-3 shadow-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <h4 className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-cyan-400 flex items-center gap-1.5">
                                <FileCode className="w-4 h-4 text-blue-500 dark:text-cyan-400" /> Executar / Importar Script SQL (.sql)
                              </h4>
                              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                Importe DDL/DML, crie tabelas e popule dados iniciais no banco "{boundDb.name}".
                              </p>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                                Caminho do Arquivo .sql no Projeto (Opcional)
                              </label>
                              <input
                                type="text"
                                placeholder="Ex: schema.sql ou /var/www/projects/..."
                                value={projectSqlFilePath}
                                onChange={(e) => setProjectSqlFilePath(e.target.value)}
                                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white font-mono focus:outline-none focus:border-blue-500"
                              />
                            </div>
                            <div className="flex items-end">
                              <button
                                type="button"
                                disabled={executingProjectSql}
                                onClick={() => handleExecuteProjectSql(boundDb.slug)}
                                className="w-full py-2 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-50 shadow-sm"
                              >
                                {executingProjectSql ? (
                                  <>
                                    <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Executando no Banco...
                                  </>
                                ) : (
                                  <>
                                    <Play className="w-3.5 h-3.5 fill-current" /> ⚡ Executar Script no Banco
                                  </>
                                )}
                              </button>
                            </div>
                          </div>

                          <div>
                            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                              Ou Cole os Comandos SQL Diretamente
                            </label>
                            <textarea
                              rows={5}
                              placeholder={"CREATE TABLE IF NOT EXISTS exemplo (\n  id INT AUTO_INCREMENT PRIMARY KEY,\n  nome VARCHAR(255) NOT NULL\n);\nINSERT INTO exemplo (nome) VALUES ('Item Teste');"}
                              value={projectSqlScript}
                              onChange={(e) => setProjectSqlScript(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs font-mono text-emerald-300 focus:outline-none focus:border-blue-500 leading-relaxed"
                            />
                          </div>

                          {projectSqlFeedback && (
                            <div className={`p-3 rounded-xl text-xs flex items-start gap-2.5 ${
                              projectSqlFeedback.success
                                ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300'
                                : 'bg-red-500/15 border border-red-500/30 text-red-300'
                            }`}>
                              {projectSqlFeedback.success ? (
                                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                              ) : (
                                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                              )}
                              <div>
                                <p className="font-semibold">{projectSqlFeedback.message}</p>
                                {projectSqlFeedback.tablesCount !== undefined && (
                                  <p className="text-[10px] text-slate-400 mt-0.5">
                                    Tabelas no banco agora: {projectSqlFeedback.tablesCount} • Tempo: {projectSqlFeedback.timeMs}ms
                                  </p>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      /* Nenhum Banco Vinculado: Card 1-Clique para Criar */
                      <div className="space-y-4">
                        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3 shadow-sm">
                          <div className="flex items-center gap-3">
                            <div className="p-3 rounded-xl bg-blue-500/10 text-blue-500 dark:bg-indigo-500/20 dark:text-indigo-400 border border-blue-500/20">
                              <Database className="w-6 h-6" />
                            </div>
                            <div>
                              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                                Provisionar Banco de Dados 1-Clique para "{activeProject.name}"
                              </h3>
                              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                Crie instantaneamente um banco isolado para este projeto e injete a <span className="text-amber-600 dark:text-amber-300 font-mono">DATABASE_URL</span> no <span className="text-blue-600 dark:text-cyan-300 font-mono">.env</span> automaticamente.
                              </p>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                            <div>
                              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Motor do Banco</label>
                              <select
                                value={newProjectDbEngine}
                                onChange={(e) => setNewProjectDbEngine(e.target.value)}
                                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-blue-500"
                              >
                                <option value="mariadb">🐬 MariaDB / MySQL (Padrão SENAI)</option>
                                <option value="postgres">🐘 PostgreSQL 16</option>
                                <option value="sqlite">📁 SQLite 3 (Arquivo Local)</option>
                              </select>
                            </div>

                            <div className="md:col-span-2">
                              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                                Script SQL Inicial no Projeto (Opcional)
                              </label>
                              <input
                                type="text"
                                placeholder="Ex: schema.sql ou banco.sql (vazio para banco limpo)"
                                value={projectSqlFilePath}
                                onChange={(e) => setProjectSqlFilePath(e.target.value)}
                                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white font-mono focus:outline-none focus:border-blue-500"
                              />
                            </div>
                          </div>

                          <div>
                            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                              Ou Cole DDL / DML Inicial (Opcional)
                            </label>
                            <textarea
                              rows={3}
                              placeholder="CREATE TABLE usuarios (...); INSERT INTO ..."
                              value={projectSqlScript}
                              onChange={(e) => setProjectSqlScript(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs font-mono text-emerald-300 focus:outline-none focus:border-blue-500"
                            />
                          </div>

                          <div className="flex items-center justify-between pt-2">
                            <span className="text-xs text-slate-500 dark:text-slate-400">
                              Nome sugerido para o banco: <span className="font-mono text-blue-600 dark:text-indigo-300">{activeProject.slug}</span>
                            </span>

                            <button
                              type="button"
                              disabled={creatingProjectDb}
                              onClick={() => handleCreateAndInjectProjectDb(activeProject.slug)}
                              className="py-2.5 px-5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center gap-2 transition cursor-pointer disabled:opacity-50 shadow-sm"
                            >
                              {creatingProjectDb ? (
                                <>
                                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Provisionando...
                                </>
                              ) : (
                                <>
                                  <Zap className="w-3.5 h-3.5 fill-current" /> Criar Banco & Injetar no .env
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
        </div>
      </div>
    );
  };

  return (
    <div className={`min-h-screen flex flex-col lg:flex-row transition-colors duration-150 ${theme === 'dark' ? 'bg-[#090d16] text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      {/* Toast Flutuante */}
      {toast && (
        <div className={`fixed bottom-5 right-5 z-[999] px-4 py-3 rounded-xl border shadow-2xl flex items-center gap-2.5 text-xs font-medium backdrop-blur-md transition-all ${
          toast.type === 'error'
            ? 'bg-red-950/95 border-red-500/50 text-red-200'
            : 'bg-emerald-950/95 border-emerald-500/50 text-emerald-200'
        }`}>
          {toast.type === 'error' ? <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" /> : <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
          <span className="whitespace-nowrap">{toast.msg}</span>
        </div>
      )}

      {/* =====================================================================
          SIDEBAR ESQUERDA
         ===================================================================== */}
      <aside className="w-full lg:w-64 bg-slate-900/90 border-b lg:border-b-0 lg:border-r border-slate-800/80 flex flex-col justify-between shrink-0">
        <div className="p-4 sm:p-5">
          {/* Logo & Versão */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 shrink-0">
                <Layers className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-sm tracking-tight text-white whitespace-nowrap">A.C.O.</span>
                  <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-md bg-blue-500/15 text-blue-400 border border-blue-500/30 whitespace-nowrap">
                    Orchestrator
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 truncate mt-0.5">Oracle Cloud • {vm.ip || '147.15.2.73'}</p>
              </div>
            </div>

            <button
              onClick={fetchOverview}
              className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white shrink-0"
              title="Atualizar"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-400' : ''}`} />
            </button>
          </div>

          {/* Botão Rápido: Novo Projeto (Design Clean Corporativo) */}
          <button
            onClick={() => {
              setActiveNav('projects');
              setShowNewProjectModal(true);
            }}
            className="mt-4 w-full py-2.5 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-sm transition cursor-pointer whitespace-nowrap"
          >
            <Plus className="w-4 h-4 stroke-[2.5] shrink-0" />
            <span>Novo Projeto</span>
          </button>

          {/* Menu de Navegação */}
          <nav className="mt-5 space-y-1">
            <button
              onClick={() => setActiveNav('projects')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition cursor-pointer whitespace-nowrap ${
                activeNav === 'projects'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <span className="flex items-center gap-2 min-w-0">
                <Rocket className="w-4 h-4 shrink-0 text-cyan-400" />
                <span className="truncate">Projetos & Aplicações</span>
              </span>
              <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-slate-800 text-slate-300 font-mono shrink-0">
                {projects.length}
              </span>
            </button>

            <button
              onClick={() => setActiveNav('databases')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition cursor-pointer whitespace-nowrap ${
                activeNav === 'databases'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <span className="flex items-center gap-2 min-w-0">
                <Database className="w-4 h-4 shrink-0 text-indigo-400" />
                <span className="truncate">Bancos de Dados 1-Clique</span>
              </span>
              <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-slate-800 text-slate-300 font-mono shrink-0">
                {databases.filter(d => !d.projectSlug && !projects.some(p => p.databaseSlug === d.slug || p.database_slug === d.slug || (d.slug === 'labw' && p.slug === 'labwarenext'))).length}
              </span>
            </button>

            <button
              onClick={() => setActiveNav('overview')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition cursor-pointer whitespace-nowrap ${
                activeNav === 'overview'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <span className="flex items-center gap-2 min-w-0">
                <Activity className="w-4 h-4 shrink-0 text-emerald-400" />
                <span className="truncate">Telemetria & A.C.O.</span>
              </span>
              <span className="text-[10px] font-mono text-emerald-400 shrink-0">
                {aco.totalRamFormatted || '...'}
              </span>
            </button>

            <button
              onClick={() => setActiveNav('hunter')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition cursor-pointer whitespace-nowrap ${
                activeNav === 'hunter'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <span className="flex items-center gap-2 min-w-0">
                <Zap className="w-4 h-4 shrink-0 text-amber-400" />
                <span className="truncate">Caçador ARM 24/7</span>
              </span>
              <span className={`w-2 h-2 rounded-full shrink-0 ${isHunting ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'}`} />
            </button>
          </nav>

          {/* Resumo Rápido da VM */}
          <div className="mt-5 p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-[11px] whitespace-nowrap">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-cyan-400 shrink-0" /> RAM VM
              </span>
              <span className="font-mono text-slate-200">{vm.memory?.used || 0}/{vm.memory?.total || 959} MB</span>
            </div>
            <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                style={{ width: `${vm.memory?.percent || 0}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] whitespace-nowrap pt-1">
              <span className="text-slate-400 flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-indigo-400 shrink-0" /> Disco SSD
              </span>
              <span className="font-mono text-slate-200">{vm.disk?.used || '5.8G'}/{vm.disk?.total || '45G'}</span>
            </div>
            <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                style={{ width: vm.disk?.percent || '13%' }}
              />
            </div>

            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400 whitespace-nowrap">
              <span>Auto-Deploy Git:</span>
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 shrink-0" /> 60s Ativo
              </span>
            </div>
          </div>
        </div>

        {/* Rodapé Integrado: Dados do Usuário + Versão & Deploy */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/60 space-y-2.5">
          {/* Usuário e Logout */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              {user.photoURL ? (
                <img src={user.photoURL} alt="Avatar" className="w-6 h-6 rounded-full border border-emerald-500/40 shrink-0" />
              ) : (
                <UserCheck className="w-5 h-5 text-emerald-400 shrink-0" />
              )}
              <div className="min-w-0">
                <p className="text-xs font-semibold text-white truncate">{user.displayName || 'William Devide'}</p>
                <p className="text-[10px] text-emerald-400 truncate">{user.email}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-300 transition cursor-pointer shrink-0"
              title="Sair"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Versão e Data de Deploy integrados e colados aos dados do usuário */}
          <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400 font-mono">
            <span className="flex items-center gap-1 text-slate-400">
              <Rocket className="w-3 h-3 text-cyan-400 shrink-0" /> {data?.acoPlatform?.version || 'v3.5.0'}
            </span>
            <span className="flex items-center gap-1 text-slate-400">
              <Clock className="w-3 h-3 text-slate-500 shrink-0" /> {data?.acoPlatform?.deployDate || '10/11/2026 08:50'}
            </span>
          </div>
        </div>
      </aside>

      {/* =====================================================================
          CONTEÚDO PRINCIPAL
         ===================================================================== */}
      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-7 overflow-y-auto space-y-6">
        {/* Topbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
          <div className="min-w-0">
            <h1 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2 truncate">
              {activeNav === 'projects' && (
                <>
                  <Rocket className="w-5 h-5 text-cyan-400 shrink-0" />
                  <span>Projetos & Aplicações Full-Stack</span>
                </>
              )}
              {activeNav === 'databases' && (
                <>
                  <Database className="w-5 h-5 text-indigo-400 shrink-0" />
                  <span>Bancos de Dados 1-Clique</span>
                </>
              )}
              {activeNav === 'overview' && (
                <>
                  <Activity className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span>Telemetria & Plataforma A.C.O. Core</span>
                </>
              )}
              {activeNav === 'hunter' && (
                <>
                  <Zap className="w-5 h-5 text-amber-400 shrink-0" />
                  <span>Robô Caçador ARM 24/7 (Ampere A1)</span>
                </>
              )}
            </h1>
            <p className="text-xs text-slate-400 truncate mt-0.5">
              Host: <span className="font-mono text-slate-300">{vm.hostname || 'vm-wdk-amd-x86'}</span> • Uptime: <span className="text-emerald-400">{vm.uptime || 'Online'}</span> • Wildcard: <span className="font-mono text-cyan-400">*.{baseDomain}</span>
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Badge Timezone Brasil */}
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>America/Sao_Paulo (UTC-3)</span>
            </div>

            {/* Alternador de Tema Light / Dark */}
            <button
              type="button"
              onClick={toggleTheme}
              className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 transition cursor-pointer shrink-0"
              title={theme === 'dark' ? 'Mudar para Tema Claro' : 'Mudar para Tema Escuro'}
            >
              {theme === 'dark' ? (
                <Sun className="w-4 h-4 text-amber-400" />
              ) : (
                <Moon className="w-4 h-4 text-indigo-400" />
              )}
            </button>

            {activeNav === 'projects' && (
              <button
                onClick={() => setShowNewProjectModal(true)}
                className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-sm transition cursor-pointer whitespace-nowrap"
              >
                <Plus className="w-4 h-4 stroke-[2.5]" />
                <span>Publicar Novo</span>
              </button>
            )}

            <button
              onClick={handleCheckGithubUpdatesNow}
              disabled={actionLoading}
              className="px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-medium text-slate-200 flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50 whitespace-nowrap"
              title="Verificar commits agora"
            >
              <Github className="w-3.5 h-3.5 text-cyan-400" />
              <span className="hidden sm:inline">Sincronizar Git</span>
            </button>

            <button
              onClick={fetchOverview}
              className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 transition cursor-pointer shrink-0"
              title="Atualizar dados"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-2.5 text-red-300 text-xs">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* -------------------------------------------------------------------
            1. ABA: PROJETOS & APLICAÇÕES
           ------------------------------------------------------------------- */}
        {activeNav === 'projects' && (
          <div className="space-y-6">
            {/* 4 Cards de Métricas Superiores */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 flex items-center justify-between min-w-0">
                <div className="min-w-0">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block truncate">Projetos Ativos</span>
                  <p className="text-xl sm:text-2xl font-bold text-white mt-0.5">{projects.length}</p>
                  <span className="text-[10px] text-emerald-400 whitespace-nowrap block truncate">HTTPS Let's Encrypt</span>
                </div>
                <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 shrink-0 ml-2">
                  <Rocket className="w-5 h-5" />
                </div>
              </div>

              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 flex items-center justify-between min-w-0">
                <div className="min-w-0">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block truncate">RAM dos Projetos</span>
                  <p className="text-xl sm:text-2xl font-bold text-cyan-300 mt-0.5 whitespace-nowrap">{totalProjectsRamMb.toFixed(1)} MB</p>
                  <span className="text-[10px] text-slate-400 whitespace-nowrap block truncate">Processos em execução</span>
                </div>
                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 shrink-0 ml-2">
                  <Cpu className="w-5 h-5" />
                </div>
              </div>

              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 flex items-center justify-between min-w-0">
                <div className="min-w-0">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block truncate">Disco dos Projetos</span>
                  <p className="text-xl sm:text-2xl font-bold text-indigo-300 mt-0.5 whitespace-nowrap">{totalProjectsDiskMb.toFixed(1)} MB</p>
                  <span className="text-[10px] text-slate-400 whitespace-nowrap block truncate">Em /var/www/projects</span>
                </div>
                <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 shrink-0 ml-2">
                  <HardDrive className="w-5 h-5" />
                </div>
              </div>

              <div
                onClick={() => setActiveNav('overview')}
                className="bg-slate-900/70 hover:bg-slate-900 border border-cyan-500/30 rounded-2xl p-4 flex items-center justify-between cursor-pointer transition min-w-0"
              >
                <div className="min-w-0">
                  <span className="text-[10px] text-cyan-400 uppercase font-bold block truncate">Plataforma A.C.O.</span>
                  <p className="text-xl sm:text-2xl font-bold text-white mt-0.5 whitespace-nowrap">
                    {aco.totalRamFormatted || '108 MB'}
                  </p>
                  <span className="text-[10px] text-slate-400 whitespace-nowrap block truncate">
                    Disco: <strong className="text-slate-200">{aco.diskFormatted || '69 MB'}</strong>
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-cyan-500/15 text-cyan-300 shrink-0 ml-2">
                  <Layers className="w-5 h-5" />
                </div>
              </div>
            </div>

            {/* Grid de Cards de Projetos */}
            {projects.length === 0 ? (
              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-10 text-center space-y-3">
                <Rocket className="w-10 h-10 text-slate-600 mx-auto" />
                <h3 className="text-sm font-bold text-white">Nenhum projeto publicado ainda</h3>
                <p className="text-xs text-slate-400">Clique no botão abaixo para publicar seu primeiro repositório com HTTPS.</p>
                <button
                  onClick={() => setShowNewProjectModal(true)}
                  className="py-2 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 text-slate-950 font-bold text-xs inline-flex items-center gap-2 cursor-pointer shadow-lg"
                >
                  <Plus className="w-4 h-4 stroke-[2.5]" /> Publicar Primeiro Projeto
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {projects.map((proj) => {
                  const isExpanded = activeProjectSlug === proj.slug;
                  return (
                    <div
                      key={proj.slug}
                      className={`border transition-all duration-200 rounded-2xl overflow-hidden ${
                        theme === 'dark' ? 'bg-[#0d131f] border-slate-800 hover:border-slate-700' : 'bg-white border-slate-200 hover:border-slate-300 shadow-sm'
                      } ${isExpanded ? (theme === 'dark' ? 'ring-1 ring-blue-500/40 border-blue-500/40' : 'ring-1 ring-blue-500/40 border-blue-500/40') : ''}`}
                    >
                      {/* Linha Resumida do Projeto (Summary Card — Alinhado Linha a Linha) */}
                      <div
                        onClick={() => {
                          if (isExpanded) {
                            setActiveProjectSlug(null);
                          } else {
                            setActiveProjectSlug(proj.slug);
                            if (!projectTab) setProjectTab('controls');
                          }
                        }}
                        className="p-4 cursor-pointer select-none hover:bg-slate-500/5 transition space-y-2.5"
                      >
                        {/* LINHA 1: Identificação Principal, Status e Ações Rápidas */}
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2.5 min-w-0">
                            {/* Seta de Expandir */}
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveProjectSlug(isExpanded ? null : proj.slug);
                                if (!isExpanded && !projectTab) setProjectTab('controls');
                              }}
                              className={`p-1 rounded-lg text-slate-400 hover:text-blue-500 transition transform ${
                                isExpanded ? 'rotate-90 text-blue-500 bg-blue-500/10' : ''
                              }`}
                              title={isExpanded ? 'Recolher detalhes' : 'Expandir no corpo da página'}
                            >
                              <ChevronRight className="w-4 h-4 transition-transform duration-200" />
                            </button>

                            {/* Nome do Projeto */}
                            <h3 className="text-base font-bold text-slate-900 dark:text-white truncate">
                              {proj.name}
                            </h3>

                            {/* Status ONLINE / PARADO */}
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase whitespace-nowrap shrink-0 flex items-center gap-1.5 ${
                              proj.status === 'running'
                                ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                                : 'bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30'
                            }`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${proj.status === "running" ? "bg-emerald-500 animate-pulse" : "bg-red-500"}`} />
                              {proj.status === 'running' ? 'ONLINE' : 'PARADO'}
                            </span>

                            {/* Stack / Tipo */}
                            <span className="px-2 py-0.5 rounded-md text-[9px] font-mono uppercase bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 whitespace-nowrap shrink-0">
                              {proj.projectType}
                            </span>
                          </div>

                          {/* Ações Rápidas do Lado Direito */}
                          <div className="flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                            <button
                              type="button"
                              onClick={() => handleManualRedeploy(proj)}
                              disabled={actionLoading}
                              className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1 cursor-pointer disabled:opacity-50 whitespace-nowrap transition shadow-sm"
                              title="Fazer Deploy Manual Agora"
                            >
                              <Rocket className="w-3.5 h-3.5 shrink-0" /> <span className="hidden sm:inline">Deploy</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => {
                                setActiveProjectSlug(isExpanded ? null : proj.slug);
                                if (!isExpanded && !projectTab) setProjectTab('controls');
                              }}
                              className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 cursor-pointer whitespace-nowrap transition ${
                                isExpanded
                                  ? 'bg-blue-600/15 text-blue-500 border border-blue-500/30'
                                  : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                              }`}
                            >
                              <Settings className="w-3.5 h-3.5 shrink-0" />
                              <span>{isExpanded ? 'Fechar' : 'Gerenciar'}</span>
                            </button>
                          </div>
                        </div>

                        {/* LINHA 2: Endereço HTTPS & Conexão Externa */}
                        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 pt-0.5">
                          <div className="flex items-center gap-2 truncate">
                            <span className="text-slate-400 dark:text-slate-500 text-[11px]">URL:</span>
                            <a
                              href={proj.url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="font-mono text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 truncate text-xs"
                              title={`Abrir ${proj.url}`}
                            >
                              <Globe className="w-3.5 h-3.5 shrink-0" />
                              <span className="truncate">{proj.url}</span>
                              <ExternalLink className="w-3 h-3 shrink-0 opacity-70" />
                            </a>
                          </div>

                          <div className="flex items-center gap-2 text-[11px] font-mono shrink-0">
                            <span>Porta: <span className="text-slate-700 dark:text-slate-300">{proj.port ? `127.0.0.1:${proj.port}` : 'Caddy Web'}</span></span>
                          </div>
                        </div>

                        {/* LINHA 3: Métricas de Recursos (RAM, Disco, BD, Commit, AutoDeploy) */}
                        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-200/70 dark:border-slate-800/80 text-[11px] font-mono">
                          {/* Recursos */}
                          <div className="flex items-center gap-3">
                            <span className="flex items-center gap-1 text-slate-600 dark:text-slate-300">
                              <Cpu className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                              <span>RAM: {proj.ramFormatted || '0 B'}</span>
                            </span>

                            <span className="flex items-center gap-1 text-slate-600 dark:text-slate-300">
                              <HardDrive className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                              <span>Disco: {proj.diskFormatted || '0 B'}</span>
                            </span>

                            {/* Indicador de Banco Vinculado na Linha de Métricas */}
                            {(proj.databaseSlug || proj.database_slug || proj.slug === 'labwarenext') ? (
                              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                                <Database className="w-3.5 h-3.5 shrink-0" />
                                <span>BD: {proj.databaseSlug || 'labw'}</span>
                              </span>
                            ) : null}
                          </div>

                          {/* Git & Status de Atualização */}
                          <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
                            <span className="flex items-center gap-1">
                              <GitCommit className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                              <span className="text-amber-600 dark:text-amber-400">#{proj.lastCommitHash || 'local'}</span>
                            </span>

                            {proj.autoDeploy !== false ? (
                              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                                <RefreshCw className="w-3 h-3 shrink-0" /> Auto-Deploy 60s
                              </span>
                            ) : (
                              <span className="text-slate-400">Deploy Manual</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Corpo Expandido no Próprio Fluxo da Página (Inline Accordion) */}
                      {isExpanded && activeProject && activeProject.slug === proj.slug && renderProjectDetails(activeProject)}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* -------------------------------------------------------------------
            2. ABA: BANCOS DE DADOS GERENCIADOS (1-CLIQUE)
           ------------------------------------------------------------------- */}
        {activeNav === 'databases' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Formulário de Criação de Banco */}
            <div className="lg:col-span-5 bg-slate-900/70 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-4">
              <div className="flex items-center gap-2.5">
                <Database className="w-5 h-5 text-cyan-400 shrink-0" />
                <h2 className="text-base font-bold text-white whitespace-nowrap">Provisionar Banco 1-Clique</h2>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Motores pré-ajustados para baixo consumo de RAM na VM, gerando <code className="text-cyan-300">DATABASE_URL</code> pronta para injetar em qualquer projeto.
              </p>

              <form onSubmit={handleCreateDatabase} className="space-y-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Nome do Banco</label>
                  <input
                    type="text"
                    required
                    placeholder="Ex: db_producao"
                    value={dbForm.name}
                    onChange={(e) => setDbForm({ ...dbForm, name: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Motor (Engine)</label>
                  <select
                    value={dbForm.engine}
                    onChange={(e) => setDbForm({ ...dbForm, engine: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="sqlite">🪶 SQLite 3 (0 MB RAM extra • Arquivo Isolado)</option>
                    <option value="postgresql">🐘 PostgreSQL 16 Tuned (~35 MB RAM)</option>
                    <option value="mysql">🐬 MariaDB / MySQL Tuned (~45 MB RAM)</option>
                    <option value="redis">⚡ Redis Cache (32 MB RAM Máx • Em Memória)</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={creatingDb}
                  className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg transition cursor-pointer disabled:opacity-50 whitespace-nowrap"
                >
                  {creatingDb ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin shrink-0" /> Criando Banco...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 shrink-0" /> Criar Banco de Dados
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Lista de Bancos Avulsos / Autônomos */}
            <div className="lg:col-span-7 space-y-4">
              {(() => {
                const standaloneDatabases = databases.filter(db => {
                  const isLinkedToProject = (db.projectSlug && db.projectSlug !== '') ||
                    projects.some(p => 
                      p.databaseSlug === db.slug || 
                      p.database_slug === db.slug || 
                      p.slug === db.slug ||
                      (db.slug === 'labw' && p.slug === 'labwarenext') ||
                      (p.slug && db.slug && p.slug.toLowerCase().includes(db.slug.toLowerCase()))
                    );
                  return !isLinkedToProject;
                });

                if (standaloneDatabases.length === 0) {
                  return (
                    <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-10 text-center space-y-3">
                      <div className="p-3 bg-slate-800/60 rounded-2xl w-fit mx-auto text-slate-400">
                        <Database className="w-8 h-8 mx-auto text-indigo-400" />
                      </div>
                      <h3 className="text-sm font-semibold text-slate-200">Nenhum banco avulso criado</h3>
                      <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                        Os bancos de dados criados para projetos (como o MariaDB de <span className="font-mono text-cyan-300">labwarenext</span>) ficam integrados diretamente no card da sua aplicação na aba <strong>Projetos</strong>.
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Utilize o formulário ao lado se precisar de uma base de dados autônoma para serviços externos.
                      </p>
                    </div>
                  );
                }

                return standaloneDatabases.map((db) => (
                  <div key={db.slug} className="bg-slate-900/75 border border-slate-800 rounded-2xl p-4 sm:p-5 space-y-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-sm font-bold text-white truncate">{db.name}</h3>
                          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 whitespace-nowrap">
                            {db.status?.toUpperCase() || 'ONLINE'}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[9px] font-mono bg-cyan-500/15 text-cyan-300 whitespace-nowrap">
                            {db.engineLabel}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5 font-mono truncate">
                          {db.host}{db.port ? `:${db.port}` : ''}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 text-[10px] font-mono text-cyan-300">
                          RAM: {db.ramFormatted || '0 B'}
                        </span>
                        <span className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 text-[10px] font-mono text-indigo-300">
                          Disco: {db.diskFormatted || '0 B'}
                        </span>
                        <button
                          onClick={() => handleDeleteDatabase(db.slug)}
                          className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 cursor-pointer"
                          title="Excluir Banco"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Connection String */}
                    <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-2">
                      <code className="text-[10px] font-mono text-amber-300 truncate">
                        DATABASE_URL={db.connectionUrl}
                      </code>
                      <button
                        onClick={() => copyToClipboard(`DATABASE_URL=${db.connectionUrl}`, 'DATABASE_URL')}
                        className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-[10px] text-cyan-300 shrink-0 flex items-center gap-1 cursor-pointer whitespace-nowrap"
                      >
                        <Copy className="w-3 h-3" /> Copiar
                      </button>
                    </div>

                    {/* Injetar em Projeto */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px]">
                      <span className="text-slate-400 whitespace-nowrap">Conectar a um projeto:</span>
                      <div className="flex items-center gap-1.5">
                        <select
                          value={dbInjectTargetProject[db.slug] || ''}
                          onChange={(e) => setDbInjectTargetProject({ ...dbInjectTargetProject, [db.slug]: e.target.value })}
                          className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-200"
                        >
                          <option value="">Escolher projeto...</option>
                          {projects.map(p => (
                            <option key={p.slug} value={p.slug}>{p.name}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          disabled={!dbInjectTargetProject[db.slug] || actionLoading}
                          onClick={() => handleInjectDatabaseIntoProject(db.slug, dbInjectTargetProject[db.slug])}
                          className="px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 text-xs font-semibold cursor-pointer disabled:opacity-40 whitespace-nowrap"
                        >
                          Injetar
                        </button>
                      </div>
                    </div>
                  </div>
                ));
              })()}
            </div>

            {/* SEÇÃO: INSPETOR VISUAL DE BANCO DE DADOS (ESTRUTURA E DADOS) */}
            <div className="lg:col-span-12 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                    <Table className="w-5 h-5 shrink-0" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white flex items-center gap-2">
                      <span>Explorador de Banco de Dados</span>
                      <span className="text-[10px] font-mono font-normal px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                        MariaDB: {selectedDbName}
                      </span>
                    </h2>
                    <p className="text-xs text-slate-400">Inspeção visual direta de estrutura (colunas/chaves) e dados reais das tabelas.</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={selectedDbName}
                    onChange={(e) => setSelectedDbName(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white font-mono"
                  >
                    <option value="labw">🐬 labw (MariaDB Principal)</option>
                    {databases.filter(d => d.engine === 'mysql').map(d => (
                      <option key={d.slug} value={d.dbName}>{d.name} ({d.dbName})</option>
                    ))}
                  </select>

                  <button
                    type="button"
                    onClick={() => {
                      fetchDbTables(selectedDbName);
                      if (selectedTable) fetchTableDetails(selectedDbName, selectedTable);
                    }}
                    className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
                    title="Recarregar dados"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingDbExplorer ? 'animate-spin text-cyan-400' : ''}`} />
                  </button>
                </div>
              </div>

              {/* Grid: Tabelas à esquerda + Visualização à direita */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* Lista de Tabelas */}
                <div className="lg:col-span-3 space-y-1 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80 max-h-96 overflow-y-auto">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-2 block mb-2">
                    Tabelas ({dbTables.length})
                  </span>
                  {dbTables.length === 0 ? (
                    <p className="text-xs text-slate-500 p-2">Nenhuma tabela encontrada no banco {selectedDbName}.</p>
                  ) : (
                    dbTables.map((tbl) => (
                      <button
                        key={tbl.name}
                        type="button"
                        onClick={() => setSelectedTable(tbl.name)}
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs transition cursor-pointer text-left ${
                          selectedTable === tbl.name
                            ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30'
                            : 'hover:bg-slate-800 text-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <Table className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="truncate">{tbl.name}</span>
                        </div>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-400 shrink-0 ml-1">
                          {tbl.estimatedRows}
                        </span>
                      </button>
                    ))
                  )}
                </div>

                {/* Painel de Dados / Estrutura da Tabela Selecionada */}
                <div className="lg:col-span-9 bg-slate-950/80 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-96">
                  {/* Topo da Tabela: Nome + Abas de Modo */}
                  <div className="p-3 bg-slate-900/90 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2 shrink-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-white">Tabela: `{selectedTable}`</span>
                      <span className="text-[10px] text-slate-400 font-mono">({tableData.total} registros)</span>
                    </div>

                    <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-xs">
                      <button
                        type="button"
                        onClick={() => setDbExplorerTab('data')}
                        className={`px-2.5 py-1 rounded-md transition cursor-pointer ${
                          dbExplorerTab === 'data'
                            ? 'bg-cyan-500 text-slate-950 font-bold'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Dados ({tableData.rows.length})
                      </button>
                      <button
                        type="button"
                        onClick={() => setDbExplorerTab('schema')}
                        className={`px-2.5 py-1 rounded-md transition cursor-pointer ${
                          dbExplorerTab === 'schema'
                            ? 'bg-cyan-500 text-slate-950 font-bold'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Estrutura ({tableSchema.length} colunas)
                      </button>
                    </div>
                  </div>

                  {/* Conteúdo da Tabela */}
                  <div className="flex-1 overflow-auto p-2 text-xs font-mono">
                    {loadingDbExplorer ? (
                      <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
                        <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
                        <span>Consultando MariaDB...</span>
                      </div>
                    ) : dbExplorerTab === 'data' ? (
                      tableData.columns.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-slate-500">
                          Tabela vazia ou sem dados para exibir.
                        </div>
                      ) : (
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="border-b border-slate-800 bg-slate-900/90 text-[11px] text-cyan-300">
                              {tableData.columns.map((c) => (
                                <th key={c} className="p-2 whitespace-nowrap font-semibold border-r border-slate-800/60 last:border-0">
                                  {c}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {tableData.rows.map((row, idx) => (
                              <tr key={idx} className="border-b border-slate-800/40 hover:bg-slate-800/40 transition">
                                {tableData.columns.map((c) => (
                                  <td key={c} className="p-2 whitespace-nowrap text-slate-300 max-w-xs truncate border-r border-slate-800/40 last:border-0" title={row[c] || ''}>
                                    {row[c] === null || row[c] === undefined ? <span className="text-slate-600 italic">NULL</span> : row[c]}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )
                    ) : (
                      /* Modo: Estrutura (Schema) */
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="border-b border-slate-800 bg-slate-900/90 text-[11px] text-cyan-300">
                            <th className="p-2 font-semibold">Coluna (Field)</th>
                            <th className="p-2 font-semibold">Tipo (Type)</th>
                            <th className="p-2 font-semibold">Nulo (Null)</th>
                            <th className="p-2 font-semibold">Chave (Key)</th>
                            <th className="p-2 font-semibold">Padrão (Default)</th>
                            <th className="p-2 font-semibold">Extra</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tableSchema.map((col) => (
                            <tr key={col.field} className="border-b border-slate-800/40 hover:bg-slate-800/40 transition">
                              <td className="p-2 font-bold text-white flex items-center gap-1.5">
                                {col.key === 'PRI' && <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1 rounded border border-amber-500/30">PK</span>}
                                {col.field}
                              </td>
                              <td className="p-2 text-cyan-300">{col.type}</td>
                              <td className="p-2 text-slate-400">{col.null}</td>
                              <td className="p-2 text-indigo-300">{col.key || '-'}</td>
                              <td className="p-2 text-slate-400">{col.default}</td>
                              <td className="p-2 text-slate-500 text-[10px]">{col.extra || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            3. ABA: TELEMETRIA GLOBAL & A.C.O. CORE
           ------------------------------------------------------------------- */}
        {activeNav === 'overview' && (
          <div className="space-y-6">
            <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-cyan-950/30 border border-cyan-500/30 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-400 shrink-0">
                    <Layers className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white whitespace-nowrap">
                      Plataforma A.C.O. Core
                    </h2>
                    <p className="text-xs text-slate-400">
                      Monitoramento em tempo real de /opt/antigravity-oracle e daemons do sistema
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="px-3.5 py-1.5 rounded-xl bg-slate-950/90 border border-cyan-500/30 text-right whitespace-nowrap">
                    <span className="text-[10px] text-slate-400 uppercase block">RAM A.C.O.</span>
                    <span className="text-base font-bold font-mono text-cyan-300">{aco.totalRamFormatted || '0 MB'}</span>
                  </div>
                  <div className="px-3.5 py-1.5 rounded-xl bg-slate-950/90 border border-indigo-500/30 text-right whitespace-nowrap">
                    <span className="text-[10px] text-slate-400 uppercase block">Disco A.C.O.</span>
                    <span className="text-base font-bold font-mono text-indigo-300">{aco.diskFormatted || '0 MB'}</span>
                  </div>
                </div>
              </div>

              {/* 3 Daemons */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                {(aco.components || []).map((comp, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between">
                    <div className="min-w-0 mr-2">
                      <p className="text-xs font-semibold text-white truncate">{comp.name}</p>
                      <span className="text-[9px] text-emerald-400 font-mono uppercase">{comp.status}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-xs font-mono text-cyan-300 shrink-0 whitespace-nowrap">
                      {comp.ramFormatted}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Tabela de Consumo Geral */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-cyan-400 shrink-0" /> Uso de RAM e Disco por Recurso
              </h3>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] whitespace-nowrap">
                      <th className="py-2.5 px-3">Recurso</th>
                      <th className="py-2.5 px-3">Tipo</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">RAM</th>
                      <th className="py-2.5 px-3">Disco</th>
                      <th className="py-2.5 px-3">Caminho / URL</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 whitespace-nowrap">
                    <tr className="bg-cyan-500/5">
                      <td className="py-2.5 px-3 font-bold text-cyan-300 flex items-center gap-2">
                        <Layers className="w-3.5 h-3.5 shrink-0" /> Plataforma A.C.O.
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-300">FastAPI + Caddy</td>
                      <td className="py-2.5 px-3">
                        <span className="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/15 text-emerald-400 font-bold">ONLINE</span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-cyan-300 font-semibold">{aco.totalRamFormatted}</td>
                      <td className="py-2.5 px-3 font-mono text-indigo-300 font-semibold">{aco.diskFormatted}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-400 truncate max-w-[200px]">/opt/antigravity-oracle</td>
                    </tr>

                    {projects.map((p) => (
                      <tr key={p.slug} className="hover:bg-slate-800/40">
                        <td
                          onClick={() => { setActiveProjectSlug(p.slug); setProjectTab('controls'); }}
                          className="py-2.5 px-3 font-semibold text-white hover:text-cyan-300 cursor-pointer truncate max-w-[180px]"
                        >
                          {p.name}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-indigo-300 uppercase">{p.projectType}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                            p.status === 'running' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
                          }`}>
                            {p.status === 'running' ? 'ONLINE' : 'PARADO'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-cyan-300">{p.ramFormatted || '0 B'}</td>
                        <td className="py-2.5 px-3 font-mono text-indigo-300">{p.diskFormatted || '0 B'}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-400 truncate max-w-[240px]">{p.url}</td>
                      </tr>
                    ))}

                    {databases.map((db) => (
                      <tr key={db.slug} className="hover:bg-slate-800/40">
                        <td className="py-2.5 px-3 font-semibold text-amber-300 flex items-center gap-1.5 truncate max-w-[180px]">
                          <Database className="w-3.5 h-3.5 shrink-0" /> {db.name}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-amber-200">{db.engineLabel}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/15 text-emerald-400 font-bold">
                            {db.status?.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-cyan-300">{db.ramFormatted}</td>
                        <td className="py-2.5 px-3 font-mono text-indigo-300">{db.diskFormatted}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-400 truncate max-w-[240px]">{db.host}{db.port ? `:${db.port}` : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            4. ABA: ROBÔ CAÇADOR ARM 24/7
           ------------------------------------------------------------------- */}
        {activeNav === 'hunter' && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-xl border shrink-0 ${
                  isHunting ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                }`}>
                  <Zap className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-base font-bold text-white whitespace-nowrap">Robô Caçador ARM (Ampere A1)</h2>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${
                      isHunting ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-300'
                    }`}>
                      {isHunting ? 'CAÇANDO 24/7' : 'PAUSADO'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Alvo: <span className="text-slate-200 font-medium">VM.Standard.A1.Flex (2 OCPU / 12GB RAM / 150GB)</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleHunterAction('trigger-now')}
                  disabled={actionLoading}
                  className="px-3.5 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                >
                  <Zap className="w-3.5 h-3.5" /> Testar Vaga Agora
                </button>
                {isHunting ? (
                  <button
                    onClick={() => handleHunterAction('stop')}
                    disabled={actionLoading}
                    className="px-3.5 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-semibold flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                  >
                    <Square className="w-3.5 h-3.5" /> Pausar
                  </button>
                ) : (
                  <button
                    onClick={() => handleHunterAction('start')}
                    disabled={actionLoading}
                    className="px-3.5 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                  >
                    <Play className="w-3.5 h-3.5" /> Ativar
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-[11px] text-slate-400 uppercase font-semibold block">Tentativas na API OCI</span>
                <div className="text-xl sm:text-2xl font-bold text-cyan-400 mt-1">{hunter.attempts || 0}</div>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-[11px] text-slate-400 uppercase font-semibold block">Última Checagem</span>
                <div className="text-xs font-semibold text-slate-200 mt-2 font-mono truncate">{hunter.last_check || 'Ativo'}</div>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-[11px] text-slate-400 uppercase font-semibold block">Retorno da Nuvem</span>
                <div className="text-xs font-medium text-amber-300 mt-2 truncate">{hunter.last_message || 'Monitorando capacidade...'}</div>
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 mb-2">
                <Terminal className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>Logs em Tempo Real (hunter_log.txt)</span>
              </div>
              <div className="bg-black/80 border border-slate-800 rounded-xl p-4 font-mono text-[11px] text-slate-300 h-56 overflow-y-auto space-y-1">
                {(hunter.recent_logs || []).map((line, idx) => (
                  <div key={idx} className="leading-relaxed">
                    {line}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* =====================================================================
          MODAL POPUP OVERLAY: NOVO PROJETO (FIXED INSET-0 Z-50)
         ===================================================================== */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
          <div
            className="relative w-full max-w-4xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden my-auto flex flex-col max-h-[92vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Topo do Modal */}
            <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800 bg-slate-950/80 shrink-0">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="p-2 rounded-xl bg-cyan-500/15 text-cyan-400 shrink-0">
                  <Rocket className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-sm sm:text-base font-bold text-white whitespace-nowrap">Publicar Novo Projeto</h2>
                  <p className="text-xs text-slate-400 truncate">Deploy automático com HTTPS Let's Encrypt para Frontend, Backend ou Full-Stack</p>
                </div>
              </div>
              <button
                onClick={() => setShowNewProjectModal(false)}
                className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition cursor-pointer shrink-0"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Conteúdo do Modal em 2 Colunas */}
            <div className="p-4 sm:p-5 overflow-y-auto">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                {/* Coluna Esquerda: Repositórios GitHub */}
                <div className="lg:col-span-5 bg-slate-950/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between space-y-3">
                  <div>
                    {/* Barra de Busca de Usuário */}
                    <div className="flex items-center justify-between gap-1.5 pb-2.5 border-b border-slate-800/80">
                      <span className="text-xs font-semibold text-cyan-400 flex items-center gap-1.5 whitespace-nowrap">
                        <Github className="w-3.5 h-3.5 shrink-0" /> GitHub
                      </span>
                      <div className="flex items-center gap-1">
                        <input
                          type="text"
                          value={ghUser}
                          onChange={(e) => setGhUser(e.target.value)}
                          className="w-24 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-[11px] text-white"
                          placeholder="Usuário"
                        />
                        <button
                          type="button"
                          onClick={() => fetchGithubRepos(ghUser)}
                          className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] text-cyan-300 cursor-pointer whitespace-nowrap"
                        >
                          Buscar
                        </button>
                      </div>
                    </div>

                    {/* Filtro do Repositório */}
                    <div className="relative mt-2.5 mb-2">
                      <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                      <input
                        type="text"
                        value={repoSearch}
                        onChange={(e) => setRepoSearch(e.target.value)}
                        placeholder="Filtrar repositório..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                      />
                    </div>

                    {/* Lista de Repositórios */}
                    <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
                      {loadingRepos ? (
                        <p className="text-xs text-slate-500 py-8 text-center">Carregando repositórios...</p>
                      ) : filteredRepos.length === 0 ? (
                        <p className="text-xs text-slate-500 py-8 text-center">Nenhum repositório encontrado.</p>
                      ) : (
                        filteredRepos.map((repo) => {
                          const isSelected = deployForm.gitUrl === (repo.clone_url || repo.cloneUrl);
                          const est = getDiskEstimate(repo.size_kb || repo.sizeKB, repo.language, deployForm.projectType);
                          return (
                            <button
                              key={repo.name}
                              type="button"
                              onClick={() => selectRepository(repo)}
                              className={`w-full text-left p-2 rounded-xl border transition flex items-center justify-between gap-2 cursor-pointer ${
                                isSelected
                                  ? 'bg-cyan-500/15 border-cyan-500/50 text-white'
                                  : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/70 text-slate-300'
                              }`}
                            >
                              <div className="min-w-0">
                                <div className="font-semibold text-xs truncate flex items-center gap-1.5" title={repo.name}>
                                  <FolderGit2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                                  <span className="truncate">{repo.name}</span>
                                </div>
                                <p className="text-[10px] text-slate-400 truncate mt-0.5">
                                  {repo.description || 'Sem descrição'}
                                </p>
                              </div>
                              <div className="flex flex-col items-end shrink-0 gap-0.5 whitespace-nowrap">
                                {repo.language && (
                                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-800 text-cyan-300 border border-slate-700">
                                    {repo.language}
                                  </span>
                                )}
                                <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-300 font-mono">
                                  ~{est.diskFormatted}
                                </span>
                              </div>
                            </button>
                          );
                        })
                      )}
                    </div>
                  </div>

                  {/* Card Estimativa de Disco (Conceito Limpo em 1 linha) */}
                  {selectedEstimate && (
                    <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-[11px] flex items-center justify-between gap-2 whitespace-nowrap">
                      <div className="truncate">
                        <span className="font-semibold text-emerald-300">Disco estimado:</span>{' '}
                        <span className="text-slate-300 font-mono font-bold">~{selectedEstimate.diskFormatted}</span>
                      </div>
                      <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-semibold shrink-0">
                        {selectedEstimate.label}
                      </span>
                    </div>
                  )}
                </div>

                {/* Coluna Direita: Formulário de Configurações */}
                <form onSubmit={handleDeployProject} className="lg:col-span-7 space-y-3.5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Nome do Projeto</label>
                      <input
                        type="text"
                        required
                        placeholder="Ex: Meu Sistema"
                        value={deployForm.name}
                        onChange={(e) => {
                          const newName = e.target.value;
                          setDeployForm({
                            ...deployForm,
                            name: newName,
                            slug: slugManuallyEdited ? deployForm.slug : sanitizeSlug(newName)
                          });
                        }}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Subdomínio HTTPS</label>
                      <div className="flex items-center bg-slate-950 border border-cyan-500/40 rounded-xl overflow-hidden">
                        <input
                          type="text"
                          required
                          placeholder="meu-app"
                          value={deployForm.slug}
                          onChange={(e) => {
                            setSlugManuallyEdited(true);
                            setDeployForm({ ...deployForm, slug: sanitizeSlug(e.target.value) });
                          }}
                          className="w-full bg-transparent px-3 py-2 text-xs text-cyan-300 font-mono focus:outline-none min-w-0"
                        />
                        <span className="px-2.5 py-2 bg-slate-900 text-[10px] text-slate-400 font-mono border-l border-slate-800 shrink-0 whitespace-nowrap">
                          .{baseDomain}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="sm:col-span-2">
                      <label className="block text-xs text-slate-400 mb-1">Arquitetura / Stack</label>
                      <select
                        value={deployForm.projectType}
                        onChange={(e) => setDeployForm({ ...deployForm, projectType: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                      >
                        <option value="auto">✨ Auto-Detectar</option>
                        <option value="fullstack">🚀 Full-Stack Monorepo (/frontend + /backend)</option>
                        <option value="react-vite">⚛️ Frontend SPA (React / Vite)</option>
                        <option value="php">🐘 Backend PHP (FastCGI / Composer / Laravel)</option>
                        <option value="python">🐍 Backend Python (FastAPI / Flask)</option>
                        <option value="node">🟢 Backend Node.js (Express / Fastify)</option>
                        <option value="static">🌐 Site Estático (HTML / CSS / JS)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Branch Git</label>
                      <input
                        type="text"
                        value={deployForm.branch}
                        onChange={(e) => setDeployForm({ ...deployForm, branch: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs text-slate-400 mb-1">URL Git do Repositório</label>
                    <input
                      type="text"
                      required
                      placeholder="https://github.com/usuario/repositorio.git"
                      value={deployForm.gitUrl}
                      onChange={(e) => setDeployForm({ ...deployForm, gitUrl: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">
                        Token Git Pessoal (Opcional)
                      </label>
                      <input
                        type="password"
                        placeholder="ghp_... (apenas para repositórios privados)"
                        value={deployForm.gitToken}
                        onChange={(e) => setDeployForm({ ...deployForm, gitToken: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">
                        Evento Cron Inicial (Opcional)
                      </label>
                      <input
                        type="text"
                        placeholder="Ex: php cron.php (ou deixe vazio)"
                        value={deployForm.cronCommand}
                        onChange={(e) => setDeployForm({ ...deployForm, cronCommand: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  </div>

                  {/* Seção Banco de Dados 1-Clique na Publicação */}
                  <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2.5">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-white">
                        <input
                          type="checkbox"
                          checked={deployForm.createDatabase}
                          onChange={(e) => setDeployForm({ ...deployForm, createDatabase: e.target.checked })}
                          className="w-4 h-4 rounded border-slate-700 accent-indigo-500 cursor-pointer"
                        />
                        <span className="flex items-center gap-1.5 text-indigo-300">
                          <Database className="w-4 h-4 text-indigo-400" /> Provisionar Banco de Dados 1-Clique
                        </span>
                      </label>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Auto-Inject DATABASE_URL
                      </span>
                    </div>

                    {deployForm.createDatabase && (
                      <div className="pt-2 border-t border-slate-800 space-y-2.5 animate-in fade-in duration-150">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                          <div>
                            <label className="block text-[11px] text-slate-400 mb-1">Motor do Banco</label>
                            <select
                              value={deployForm.databaseEngine}
                              onChange={(e) => setDeployForm({ ...deployForm, databaseEngine: e.target.value })}
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                            >
                              <option value="mariadb">🐬 MariaDB / MySQL (Padrão SENAI)</option>
                              <option value="postgres">🐘 PostgreSQL 16</option>
                              <option value="sqlite">📁 SQLite 3</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-[11px] text-slate-400 mb-1">Arquivo .sql no Repositório (Opcional)</label>
                            <input
                              type="text"
                              placeholder="Ex: schema.sql ou banco.sql"
                              value={deployForm.initialSqlFile}
                              onChange={(e) => setDeployForm({ ...deployForm, initialSqlFile: e.target.value })}
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-[11px] text-slate-400 mb-1">Ou Cole os Comandos DDL / DML (Opcional)</label>
                          <textarea
                            rows={2}
                            placeholder="CREATE TABLE IF NOT EXISTS ..."
                            value={deployForm.initialSql}
                            onChange={(e) => setDeployForm({ ...deployForm, initialSql: e.target.value })}
                            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-emerald-300 font-mono focus:outline-none focus:border-indigo-500"
                          />
                        </div>

                        <p className="text-[10px] text-slate-400">
                          💡 O A.C.O. criará o banco, executará o script SQL e injetará as credenciais completas em <span className="text-amber-300 font-mono">DATABASE_URL</span> no arquivo <span className="text-cyan-300 font-mono">.env</span>.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Variáveis .env + Auto Deploy Toggle */}
                  <div>
                    <div className="flex items-center justify-between mb-1 text-xs">
                      <label className="text-slate-400 flex items-center gap-1.5 whitespace-nowrap">
                        <Key className="w-3.5 h-3.5 text-amber-400 shrink-0" /> Variáveis (.env)
                      </label>
                      <label className="flex items-center gap-1.5 text-emerald-400 cursor-pointer whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={deployForm.autoDeploy}
                          onChange={(e) => setDeployForm({ ...deployForm, autoDeploy: e.target.checked })}
                          className="rounded border-slate-700 accent-emerald-500"
                        />
                        <span>Auto-Deploy (GitHub)</span>
                      </label>
                    </div>
                    <textarea
                      rows={2}
                      placeholder={"PORT=8080\nDATABASE_URL=sqlite:////var/lib/aco-databases/meu_db.sqlite"}
                      value={deployForm.envVarsText}
                      onChange={(e) => setDeployForm({ ...deployForm, envVarsText: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-amber-200 font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  {/* Rodapé do Form */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                    <div className="text-[11px] text-slate-400 truncate max-w-[280px]">
                      URL: <span className="font-mono text-cyan-300 font-semibold truncate">https://{deployForm.customDomain || `${deployForm.slug || 'meu-app'}.${baseDomain}`}</span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => setShowNewProjectModal(false)}
                        className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 cursor-pointer whitespace-nowrap"
                      >
                        Fechar
                      </button>
                      <button
                        type="submit"
                        disabled={deploying}
                        className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-sm transition cursor-pointer disabled:opacity-50 whitespace-nowrap"
                      >
                        {deploying ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0" /> Publicando...
                          </>
                        ) : (
                          <>
                            <Rocket className="w-3.5 h-3.5 shrink-0" /> Fazer Deploy
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </form>
              </div>

              {/* Log do Deploy */}
              {deployResult && (
                <div className={`mt-4 p-3.5 rounded-xl border text-xs font-mono whitespace-pre-wrap max-h-56 overflow-y-auto ${
                  deployResult.status === 'success' || deployResult.ok
                    ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
                    : 'bg-red-950/40 border-red-500/40 text-red-200'
                }`}>
                  <div className="font-bold mb-1">
                    {deployResult.status === 'success' || deployResult.ok
                      ? `✅ Sucesso! Acesse: ${deployResult.project?.url}`
                      : `❌ Erro: ${deployResult.message || 'Falha no build'}`}
                  </div>
                  {deployResult.log}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
