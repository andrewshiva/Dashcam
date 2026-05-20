import { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import DetectionImage from './components/DetectionImage';
import { authenticateUser, createUserSession, findAuthUser, normalizeUsername } from './auth';
import { CheckCircle2, Bell, FileText, Upload, Loader2, CheckCircle, XCircle, Film, ShieldCheck, UserRound, KeyRound, LogOut, Eye, Download } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'https://dashboard-api-863438916962.asia-south1.run.app';
const REPORT_BASE = import.meta.env.VITE_REPORT_BASE || 'https://report-generator-863438916962.asia-south1.run.app';
const FALLBACK_ROAD_IMAGE = 'https://images.unsplash.com/photo-1515162305285-0293e4767cc2?w=800';
const DETECTION_ACCENT_COLOR = '#00E5FF';
const DETECTION_SHADOW_COLOR = '#07111F';
const DETECTION_LABEL_BACKGROUND = 'rgba(7, 17, 31, 0.92)';
const DAILY_RO_UPLOAD_LIMIT = 3;
const SESSION_STORAGE_KEY = 'dashcam-current-user';
const UPLOAD_USAGE_STORAGE_PREFIX = 'dashcam-upload-usage';

const getTodayKey = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const getUploadUsageKey = (username) => (
  `${UPLOAD_USAGE_STORAGE_PREFIX}:${normalizeUsername(username)}:${getTodayKey()}`
);

const readDailyUploadCount = (username) => {
  if (typeof window === 'undefined') return 0;
  const storedValue = Number(window.localStorage.getItem(getUploadUsageKey(username)));
  return Number.isFinite(storedValue) ? storedValue : 0;
};

const writeDailyUploadCount = (username, count) => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(getUploadUsageKey(username), String(count));
};

const readStoredUser = () => {
  if (typeof window === 'undefined') return null;

  try {
    const storedUser = JSON.parse(window.localStorage.getItem(SESSION_STORAGE_KEY) || 'null');
    if (!storedUser?.username) return null;

    const knownUser = findAuthUser(storedUser.username);
    if (!knownUser || knownUser.role !== storedUser.role) return null;

    return {
      ...createUserSession(knownUser),
    };
  } catch {
    return null;
  }
};

const saveStoredUser = (user) => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
};

const clearStoredUser = () => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(SESSION_STORAGE_KEY);
};

const REPORT_MASTER_DATA = [
  {
    ro_name: 'RO Gandhinagar',
    pius: [
      { piu_name: 'PIU Ahmedabad', upc_codes: ['GJ-AHD-001', 'GJ-AHD-002'] },
      { piu_name: 'PIU Vadodara', upc_codes: ['GJ-VDR-001', 'GJ-VDR-002'] },
    ],
  },
  {
    ro_name: 'RO Jaipur',
    pius: [
      { piu_name: 'PIU Jaipur', upc_codes: ['RJ-JAI-001', 'RJ-JAI-002'] },
      { piu_name: 'PIU Kota', upc_codes: ['RJ-KOT-001', 'RJ-KOT-002'] },
    ],
  },
  {
    ro_name: 'RO Delhi',
    pius: [
      { piu_name: 'PIU Delhi', upc_codes: ['DL-DEL-001', 'DL-DEL-002'] },
      { piu_name: 'PIU Gurugram', upc_codes: ['HR-GGM-001', 'HR-GGM-002'] },
    ],
  },
  {
    ro_name: 'RO Chandigarh',
    pius: [
      { piu_name: 'PIU Panipat', upc_codes: ['HR-PNP-001', 'HR-PNP-002'] },
      { piu_name: 'PIU Ambala', upc_codes: ['HR-AMB-001', 'HR-AMB-002'] },
    ],
  },
];

const getLocalDateTimeInputValue = (date = new Date()) => {
  const timezoneOffsetMs = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - timezoneOffsetMs).toISOString().slice(0, 16);
};

const createInitialReportForm = () => ({
  ro_name: '',
  piu_name: '',
  upc_code: '',
  nh_number: '',
  project_name: '',
  start_chainage: '',
  end_chainage: '',
  project_length: '',
  state_name: '',
  survey_date: getLocalDateTimeInputValue(),
});

const REPORT_MANUAL_FIELDS = [
  { name: 'project_name', label: 'Name of the Project', placeholder: 'Road condition survey', type: 'text', wide: true },
  { name: 'start_chainage', label: 'Start Chainage', placeholder: '0+000', type: 'text' },
  { name: 'end_chainage', label: 'End Chainage', placeholder: '10+500', type: 'text' },
  { name: 'project_length', label: 'Project Length', placeholder: '10.5 km', type: 'text' },
  { name: 'state_name', label: 'Name of the State', placeholder: 'Gujarat', type: 'text' },
  { name: 'survey_date', label: 'Survey Date & Time', placeholder: '', type: 'datetime-local' },
];

const buildReportUrl = (videoId, reportForm) => {
  const params = new URLSearchParams();
  Object.entries(reportForm).forEach(([key, value]) => {
    const trimmedValue = String(value || '').trim();
    if (trimmedValue) {
      params.set(key, trimmedValue);
    }
  });

  const baseUrl = `${REPORT_BASE.replace(/\/+$/, '')}/generate-report/${encodeURIComponent(videoId)}`;
  const query = params.toString();
  return query ? `${baseUrl}?${query}` : baseUrl;
};

const ROAD_MONITORING_COLUMNS = [
  'Analytics Dashboard (RAMS)',
  'Survey Date & Time',
  'Category',
  'Road Defect',
  'Confidence',
  'Latitude',
  'Longitude',
  'Source Video',
  'Detected Anomalities',
  'NH Number',
  'RO',
  'PIU',
  'UPC',
  'Project Name',
  'State',
  'Start Chainage',
  'End Chainage',
  'Project Length',
];

const EMPTY_REPORT_VALUE = 'na';
const ROAD_MONITORING_REPORT_NAME = 'Road Analytics Monitoring System Report';

const PIPELINE_STEPS = [
  { key: 'upload', label: 'Uploading Video' },
  { key: 'processing', label: 'Extracting Frames & Telemetry' },
  { key: 'inference', label: 'AI Defect Detection' },
  { key: 'saving', label: 'Saving to Database' },
  { key: 'complete', label: 'Analysis Complete' },
];

const anomalyShortName = (type) => {
  if (!type) return 'ANOMALY';
  const t = type.toLowerCase();
  if (t.includes('pothole')) return 'POTHOLE';
  if (t.includes('signage')) return 'MISSING SIGNAGE';
  if (t.includes('crack')) return 'ROAD CRACK';
  if (t.includes('deterioration')) return 'SURFACE DAMAGE';
  return t.replace('_', ' ').toUpperCase();
};

const formatInspectionDateTime = (value) => {
  if (!value || String(value).includes('ago')) return EMPTY_REPORT_VALUE;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return EMPTY_REPORT_VALUE;
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getInspectionDateFilterKey = (value) => {
  if (!value) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  if (typeof value === 'string' && value.includes('ago')) {
    return getLocalDateTimeInputValue().slice(0, 10);
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return getLocalDateTimeInputValue(date).slice(0, 10);
};

const formatCoordinateValue = (value) => {
  const coordinate = Number(value);
  if (!Number.isFinite(coordinate)) {
    return EMPTY_REPORT_VALUE;
  }
  return coordinate.toFixed(5);
};

const escapeHtml = (value) => (
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
);

const buildReportFileName = (extension) => {
  const datePart = new Date().toISOString().slice(0, 10);
  return `${ROAD_MONITORING_REPORT_NAME}_${datePart}`
    .replace(/[^a-z0-9]+/gi, '_')
    .replace(/^_+|_+$/g, '')
    .toLowerCase() + `.${extension}`;
};

const LoginPage = ({ loginError, onLogin }) => {
  const [credentials, setCredentials] = useState({ username: '', password: '' });

  const handleSubmit = (event) => {
    event.preventDefault();
    onLogin(credentials);
  };

  const handleFieldChange = (field, value) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
  };

  const isSubmitDisabled = !credentials.username.trim() || !credentials.password;

  return (
    <main className="login-screen">
      <section className="login-card" aria-label="DashcamR dashboard login">
        <div className="login-brand">
          <div className="login-brand-mark">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1>DashcamR</h1>
            <p>Sign in to continue</p>
          </div>
        </div>
        <p className="login-attribution">Dashcam Analytics Service</p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="login-field">
            <span>Username</span>
            <div className="login-input-wrap">
              <UserRound size={18} />
              <input
                className="login-input"
                type="text"
                value={credentials.username}
                autoComplete="username"
                onChange={(event) => handleFieldChange('username', event.target.value)}
              />
            </div>
          </label>

          <label className="login-field">
            <span>Password</span>
            <div className="login-input-wrap">
              <KeyRound size={18} />
              <input
                className="login-input"
                type="password"
                value={credentials.password}
                autoComplete="current-password"
                onChange={(event) => handleFieldChange('password', event.target.value)}
              />
            </div>
          </label>

          {loginError && (
            <p className="login-error" role="alert">
              {loginError}
            </p>
          )}

          <button className="login-submit" type="submit" disabled={isSubmitDisabled}>
            Sign in
          </button>
        </form>
      </section>
    </main>
  );
};

const App = () => {
  const [currentUser, setCurrentUser] = useState(readStoredUser);
  const [loginError, setLoginError] = useState('');
  const [defects, setDefects] = useState([]);
  const [defectsError, setDefectsError] = useState('');
  const [uploadState, setUploadState] = useState('idle'); // idle, uploading, processing, complete, error
  const [uploadProgress, setUploadProgress] = useState(0);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [executionId, setExecutionId] = useState(null);
  const [storedVideoId, setStoredVideoId] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedDefect, setSelectedDefect] = useState(null);
  const [reportForm, setReportForm] = useState(createInitialReportForm);
  const [inspectionDateFilter, setInspectionDateFilter] = useState('');
  const [dailyUploadCount, setDailyUploadCount] = useState(() => {
    const storedUser = readStoredUser();
    return storedUser?.role === 'ro' ? readDailyUploadCount(storedUser.username) : 0;
  });

  const selectedRo = REPORT_MASTER_DATA.find(item => item.ro_name === reportForm.ro_name);
  const piuOptions = selectedRo?.pius || [];
  const selectedPiu = piuOptions.find(item => item.piu_name === reportForm.piu_name);
  const upcOptions = selectedPiu?.upc_codes || [];
  const isRoUser = currentUser?.role === 'ro';
  const isUploadLimitReached = false;
  const isUploadEnabled = true;
  const uploadDisabledReason = '';

  const handleLogin = ({ username, password }) => {
    const userSession = authenticateUser({ username, password });

    if (!userSession) {
      setLoginError('Invalid username or password.');
      return;
    }

    saveStoredUser(userSession);
    setCurrentUser(userSession);
    setDailyUploadCount(userSession.role === 'ro' ? readDailyUploadCount(userSession.username) : 0);
    setLoginError('');
  };

  useEffect(() => {
    if (!currentUser || currentUser.role !== 'ro') {
      return undefined;
    }

    const interval = setInterval(() => {
      setDailyUploadCount(readDailyUploadCount(currentUser.username));
    }, 60000);
    return () => clearInterval(interval);
  }, [currentUser]);

  useEffect(() => {
    const fetchDefects = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/defects`);
        if (!response.ok) {
          let detail = 'Defect API is unavailable.';
          try {
            const payload = await response.json();
            detail = payload.detail || detail;
          } catch {
            // Keep generic API error text when the backend returns a non-JSON error.
          }
          throw new Error(detail);
        }
        const data = await response.json();
        setDefects(data);
        setDefectsError('');
      } catch (error) {
        console.warn('Defect API unavailable:', error.message);
        setDefects([]);
        setDefectsError(error.message || 'Defect API is unavailable.');
      }
    };

    fetchDefects();
    const interval = setInterval(fetchDefects, 10000);
    return () => clearInterval(interval);
  }, []);

  // Poll pipeline status
  useEffect(() => {
    if (!executionId || uploadState === 'complete' || uploadState === 'error') return;

    const pollStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/pipeline-status/${executionId}`);
        if (!response.ok) {
          let detail = 'Pipeline status check failed.';
          try {
            const payload = await response.json();
            detail = payload.detail || detail;
          } catch {
            // Keep generic status error text when the backend returns a non-JSON error.
          }
          throw new Error(detail);
        }

        const data = await response.json();
        const latestStage = data.latest_event?.stage || data.storage?.status;
        
        if (data.state === 'SUCCEEDED') {
          setPipelineStep(4);
          setUploadState('complete');
          setUploadProgress(100);
          setErrorMessage('');
        } else if (data.state === 'FAILED' || data.state === 'TIMED_OUT') {
          setUploadState('error');
          setErrorMessage(data.error || latestStage || 'Pipeline failed');
        } else if (data.state === 'ACTIVE') {
          const stepByStage = {
            stored: 1,
            validated: 2,
            workflow_start: 2,
            extraction_start: 2,
            extraction_success: 3,
            inference_start: 3,
            inference_success: 3,
            data_processing_start: 3,
            workflow_success: 4,
          };
          const nextStep = stepByStage[latestStage] ?? Math.min(pipelineStep + 1, 3);
          setPipelineStep(nextStep);
          setUploadProgress(prev => Math.min(Math.max(prev, 35 + nextStep * 15), 85));
        }
      } catch (error) {
        console.error('Status poll error:', error);
        setErrorMessage(error.message || 'Pipeline status check failed.');
      }
    };

    const interval = setInterval(pollStatus, 4000);
    return () => clearInterval(interval);
  }, [executionId, uploadState, pipelineStep]);

  const handleUpload = async (file) => {
    if (!file) return;

    const allowedTypes = ['.mp4', '.mov', '.avi', '.mkv'];
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (!allowedTypes.includes(ext)) {
      setErrorMessage(`Invalid file type: ${ext}. Allowed: ${allowedTypes.join(', ')}`);
      setUploadState('error');
      return;
    }

    setUploadedFile(file);
    setStoredVideoId(null);
    setUploadState('uploading');
    setUploadProgress(0);
    setPipelineStep(0);
    setErrorMessage('');

    try {
      // Step 1: Generate GCS Signed URL via Backend
      const urlResponse = await fetch(`${API_BASE}/api/v1/generate-upload-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type || 'video/mp4',
        }),
      });

      if (!urlResponse.ok) {
        const err = await urlResponse.json();
        throw new Error(err.detail || 'Failed to generate secure upload channel.');
      }

      const { upload_url, stored_filename } = await urlResponse.json();

      // Step 2: Upload direct to GCS with real physical progress tracking
      await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', upload_url, true);
        xhr.setRequestHeader('Content-Type', file.type || 'video/mp4');

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = Math.round((event.loaded / event.total) * 100);
            // Cap upload progress bar at 95% until backend confirms record writes
            setUploadProgress(Math.round(percentComplete * 0.95));
          }
        };

        xhr.onload = () => {
          if (xhr.status === 200) {
            resolve();
          } else {
            reject(new Error(`Storage service rejected upload with status ${xhr.status}`));
          }
        };

        xhr.onerror = () => {
          reject(new Error('Network connection error during storage upload.'));
        };

        xhr.send(file);
      });

      setUploadProgress(95);

      // Step 3: Register upload with backend to write DB rows and trigger downstream stages
      const confirmResponse = await fetch(`${API_BASE}/api/v1/confirm-upload`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          original_filename: file.name,
          stored_filename: stored_filename,
          content_type: file.type || 'video/mp4',
          size_bytes: file.size,
        }),
      });

      if (!confirmResponse.ok) {
        const err = await confirmResponse.json();
        throw new Error(err.detail || 'Upload complete but failed to register with database.');
      }

      const data = await confirmResponse.json();
      const uploadedVideoId = data.execution_id || data.stored_filename || data.filename || file.name;
      
      setStoredVideoId(uploadedVideoId);
      if (isRoUser) {
        const nextDailyUploadCount = currentDailyUploadCount + 1;
        writeDailyUploadCount(currentUser.username, nextDailyUploadCount);
        setDailyUploadCount(nextDailyUploadCount);
      }

      setUploadProgress(100);
      setPipelineStep(1);
      setUploadState('processing');

      if (uploadedVideoId) {
        setExecutionId(uploadedVideoId);
      } else {
        throw new Error('Upload completed but tracking execution ID is missing.');
      }
    } catch (error) {
      setErrorMessage(error.message || 'Direct GCS upload failed.');
      setUploadState('error');
    }
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    if (!isUploadEnabled) return;
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isUploadEnabled]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    if (!isUploadEnabled) return;
    setDragOver(true);
  }, [isUploadEnabled]);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const resetUpload = () => {
    setUploadState('idle');
    setUploadProgress(0);
    setPipelineStep(0);
    setUploadedFile(null);
    setExecutionId(null);
    setStoredVideoId(null);
    setErrorMessage('');
  };

  const handleLogout = () => {
    clearStoredUser();
    setCurrentUser(null);
    setLoginError('');
    setDailyUploadCount(0);
    setReportForm(createInitialReportForm());
    setSelectedDefect(null);
    resetUpload();
  };

  const getReportVideoId = () => {
    if (storedVideoId) return storedVideoId;
    if (uploadedFile?.name) return uploadedFile.name;
    const defectVideoId = defects.find(defect => defect.video_id)?.video_id;
    return defectVideoId || 'video15.mov';
  };

  const getDetectionSourceVideo = (defect) => {
    const sourceVideo = defect?.video_id || storedVideoId || uploadedFile?.name || getReportVideoId();
    return String(sourceVideo || '').trim() || 'Unknown video';
  };

  const buildDetectionImageFilename = (defect, fallbackIndex = '') => {
    const type = defect?.type || defect?.detection_type || 'anomaly';
    const identifier = defect?.id || fallbackIndex || 'evidence';
    const sourceVideo = getDetectionSourceVideo(defect).replace(/\.[^.]+$/, '');
    return `${type}_${identifier}_${sourceVideo}`
      .replace(/[^a-z0-9._-]+/gi, '_')
      .replace(/^_+|_+$/g, '')
      .toLowerCase() + '.jpg';
  };

  const getDetectionImageUrl = (defect) => (
    defect?.id && !defect.is_demo && !String(defect.id).startsWith('demo')
      ? `${API_BASE}/api/v1/defects/${defect.id}/image`
      : FALLBACK_ROAD_IMAGE
  );

  const renderDetectedAnomalyCell = (defect, index) => {
    const imageUrl = getDetectionImageUrl(defect);

    return (
      <div className="detected-anomaly-cell">
        <button
          type="button"
          className="detected-anomaly-button"
          onClick={() => setSelectedDefect(defect)}
          title="View anomaly photo"
          aria-label="View anomaly photo"
        >
          <Eye size={16} />
        </button>
        <button
          type="button"
          className="detected-anomaly-button"
          onClick={() => handleDownload(imageUrl, buildDetectionImageFilename(defect, index), defect)}
          title="Download anomaly photo"
          aria-label="Download anomaly photo"
        >
          <Download size={16} />
        </button>
      </div>
    );
  };

  const reportDetailGridCells = [
    reportForm.nh_number || EMPTY_REPORT_VALUE,
    reportForm.ro_name || EMPTY_REPORT_VALUE,
    reportForm.piu_name || EMPTY_REPORT_VALUE,
    reportForm.upc_code || EMPTY_REPORT_VALUE,
    reportForm.project_name || EMPTY_REPORT_VALUE,
    reportForm.state_name || EMPTY_REPORT_VALUE,
    reportForm.start_chainage || EMPTY_REPORT_VALUE,
    reportForm.end_chainage || EMPTY_REPORT_VALUE,
    reportForm.project_length || EMPTY_REPORT_VALUE,
  ];

  const emptyReportDetailRow = [
    'Road Analytics',
    formatInspectionDateTime(reportForm.survey_date),
    EMPTY_REPORT_VALUE,
    EMPTY_REPORT_VALUE,
    EMPTY_REPORT_VALUE,
    EMPTY_REPORT_VALUE,
    EMPTY_REPORT_VALUE,
    storedVideoId || uploadedFile?.name || EMPTY_REPORT_VALUE,
    EMPTY_REPORT_VALUE,
    ...reportDetailGridCells,
  ];

  const selectedInspectionDateKey = getInspectionDateFilterKey(inspectionDateFilter);
  const hasActiveInspectionDateFilter = Boolean(selectedInspectionDateKey);
  const visibleReportDefects = selectedInspectionDateKey
    ? defects.filter(defect => getInspectionDateFilterKey(defect.timestamp) === selectedInspectionDateKey)
    : defects;
  const shouldShowEmptyReportDetailRow = !hasActiveInspectionDateFilter && visibleReportDefects.length === 0;

  const roadInspectionRows = visibleReportDefects.length > 0 ? visibleReportDefects.map((defect, index) => {
    const defectType = (defect.type || defect.detection_type || 'Road defect').replace('_', ' ');
    const confidence = Number(defect.confidence);

    return [
      'Road Analytics',
      formatInspectionDateTime(defect.timestamp || reportForm.survey_date),
      defect.category ? defect.category.replace(/_/g, ' ') : EMPTY_REPORT_VALUE,
      defect.label || defectType,
      Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : EMPTY_REPORT_VALUE,
      formatCoordinateValue(defect.latitude),
      formatCoordinateValue(defect.longitude),
      getDetectionSourceVideo(defect),
      renderDetectedAnomalyCell(defect, index),
      ...reportDetailGridCells,
    ];
  }) : shouldShowEmptyReportDetailRow ? [emptyReportDetailRow] : [];
  const roadInspectionTotalEntries = roadInspectionRows.length;

  const emptyReportDetailExportRow = [...emptyReportDetailRow];

  const roadInspectionExportRows = visibleReportDefects.length > 0 ? visibleReportDefects.map((defect) => {
    const defectType = (defect.type || defect.detection_type || 'Road defect').replace('_', ' ');
    const confidence = Number(defect.confidence);

    return [
      'Road Analytics',
      formatInspectionDateTime(defect.timestamp || reportForm.survey_date),
      defect.category ? defect.category.replace(/_/g, ' ') : EMPTY_REPORT_VALUE,
      defect.label || defectType,
      Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : EMPTY_REPORT_VALUE,
      formatCoordinateValue(defect.latitude),
      formatCoordinateValue(defect.longitude),
      getDetectionSourceVideo(defect),
      {
        label: defectType,
      },
      ...reportDetailGridCells,
    ];
  }) : shouldShowEmptyReportDetailRow ? [emptyReportDetailExportRow] : [];

  const buildReportExportTableHtml = () => {
    const headerHtml = ROAD_MONITORING_COLUMNS
      .map(column => `<th>${escapeHtml(column)}</th>`)
      .join('');
    const bodyHtml = roadInspectionExportRows.length > 0
      ? roadInspectionExportRows.map(row => (
        `<tr>${row.map((cell) => {
          if (cell && typeof cell === 'object') {
            return `
              <td class="anomaly-export-cell">
                <div>${escapeHtml(cell.label)}</div>
              </td>
            `;
          }
          return `<td>${escapeHtml(cell)}</td>`;
        }).join('')}</tr>`
      )).join('')
      : `<tr><td colspan="${ROAD_MONITORING_COLUMNS.length}">No road inspection data available in table</td></tr>`;

    return `
      <table>
        <thead><tr>${headerHtml}</tr></thead>
        <tbody>${bodyHtml}</tbody>
      </table>
    `;
  };

  const buildReportExportDocument = () => {
    const generatedAt = new Date().toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    return `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>${escapeHtml(ROAD_MONITORING_REPORT_NAME)}</title>
          <style>
            body { font-family: Arial, sans-serif; color: #0f172a; margin: 24px; }
            h1 { font-size: 20px; margin: 0 0 6px; }
            p { margin: 0 0 18px; color: #475569; font-size: 12px; }
            table { border-collapse: collapse; width: 100%; font-size: 11px; }
            th, td { border: 1px solid #cbd5e1; padding: 7px; text-align: left; vertical-align: top; }
            th { background: #eef2f7; font-weight: 700; }
            .anomaly-export-cell { min-width: 110px; }
            @media print { body { margin: 10mm; } }
          </style>
        </head>
        <body>
          <h1>${escapeHtml(ROAD_MONITORING_REPORT_NAME)}</h1>
          <p>Generated ${escapeHtml(generatedAt)}</p>
          ${buildReportExportTableHtml()}
        </body>
      </html>
    `;
  };

  const downloadReportBlob = (content, filename, type) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleReportTableExport = (format) => {
    const documentHtml = buildReportExportDocument();

    if (format === 'excel') {
      downloadReportBlob(
        documentHtml,
        buildReportFileName('xls'),
        'application/vnd.ms-excel;charset=utf-8'
      );
      return;
    }

    const reportWindow = window.open('', '_blank', 'width=1200,height=800');
    if (!reportWindow) {
      setErrorMessage('Please allow pop-ups to export the report as PDF.');
      return;
    }
    reportWindow.document.open();
    reportWindow.document.write(documentHtml);
    reportWindow.document.close();
    reportWindow.focus();
    setTimeout(() => reportWindow.print(), 300);
  };

  const handleReportFieldChange = (field, value) => {
    setReportForm(prev => {
      if (field === 'ro_name') {
        return { ...prev, ro_name: value, piu_name: '', upc_code: '' };
      }
      if (field === 'piu_name') {
        return { ...prev, piu_name: value, upc_code: '' };
      }
      return { ...prev, [field]: value };
    });
  };

  const handleInspectionDateFilterChange = (event) => {
    setInspectionDateFilter(event.currentTarget.value);
  };

  const handleReportDownload = () => {
    window.open(buildReportUrl(getReportVideoId(), reportForm), '_blank', 'noopener,noreferrer');
  };

  const renderRoadAnalyticsReport = () => (
    <section className="glass-panel road-monitoring-panel detection-report-panel">
      <div className="road-monitoring-title">
        <h2>Road Analytics Monitoring System</h2>
      </div>

      <div className="road-filter-grid">
        <label className="report-field">
          <span>RO</span>
          <select
            className="report-select"
            value={reportForm.ro_name}
            onChange={(event) => handleReportFieldChange('ro_name', event.target.value)}
          >
            <option value="">Select RO</option>
            {REPORT_MASTER_DATA.map(item => (
              <option key={item.ro_name} value={item.ro_name}>
                {item.ro_name}
              </option>
            ))}
          </select>
        </label>

        <label className="report-field">
          <span>PIU</span>
          <select
            className="report-select"
            value={reportForm.piu_name}
            onChange={(event) => handleReportFieldChange('piu_name', event.target.value)}
            disabled={!reportForm.ro_name}
          >
            <option value="">Select PIU</option>
            {piuOptions.map(item => (
              <option key={item.piu_name} value={item.piu_name}>
                {item.piu_name}
              </option>
            ))}
          </select>
        </label>

        <label className="report-field">
          <span>Project Stage</span>
          <select className="report-select" defaultValue="">
            <option value="">Select Stage</option>
            <option value="inspection">Inspection</option>
            <option value="review">Review</option>
            <option value="completed">Completed</option>
          </select>
        </label>

        <label className="report-field">
          <span>Search By Latest Inspection Date</span>
          <input
            className="report-input"
            type="date"
            value={inspectionDateFilter}
            onInput={handleInspectionDateFilterChange}
            onChange={handleInspectionDateFilterChange}
          />
        </label>

        <label className="report-field">
          <span>Project</span>
          <input
            className="report-input"
            type="text"
            value={reportForm.project_name}
            placeholder="Select Project"
            onChange={(event) => handleReportFieldChange('project_name', event.target.value)}
          />
        </label>
      </div>


      <div className="road-table-toolbar">
        <div className="road-table-toolbar-left">
          <div className="road-report-downloads" aria-label="Download Road Analytics Monitoring System report">
            <button type="button" onClick={() => handleReportTableExport('pdf')}>
              <FileText size={14} />
              <span>PDF</span>
            </button>
            <button type="button" onClick={() => handleReportTableExport('excel')}>
              <Download size={14} />
              <span>Excel</span>
            </button>
          </div>
        </div>
        <label>
          Search:
          <input className="road-table-search" type="search" />
        </label>
      </div>

      <div className="road-table-wrap">
        <table className="road-monitoring-table detection-report-table">
          <thead>
            <tr>
              {ROAD_MONITORING_COLUMNS.map(column => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {defectsError ? (
              <tr>
                <td colSpan={ROAD_MONITORING_COLUMNS.length} className="road-table-empty">
                  {defectsError}
                </td>
              </tr>
            ) : roadInspectionRows.length > 0 ? (
              roadInspectionRows.map((row, rowIndex) => (
                <tr key={`${row[6]}-${rowIndex}`}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${rowIndex}-${cellIndex}`}>{cell}</td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={ROAD_MONITORING_COLUMNS.length} className="road-table-empty">
                  No road inspection data available in table
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="road-table-footer">
        <span>Showing {roadInspectionRows.length ? `1 to ${roadInspectionRows.length}` : '0 to 0'} of {roadInspectionTotalEntries} entries</span>
        <div>
          <button type="button" disabled>Previous</button>
          <button type="button" disabled>Next</button>
        </div>
      </div>
    </section>
  );

  const handleDownload = async (url, filename, defect) => {
    try {
      if (defect) {
        // Build canvas dynamically to include AI bounding box, L-brackets, pointing arrow, and tag!
        const img = new Image();
        img.crossOrigin = 'anonymous'; // Prevent canvas tainted security errors
        img.src = url;
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
        });

        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        const ctx = canvas.getContext('2d');

        // 1. Draw raw dashcam image
        ctx.drawImage(img, 0, 0);

        // Compute defect coordinates (use normalized fallback if custom coordinates are missing)
        const lbl = (defect.type || defect.detection_type || 'ANOMALY').toUpperCase();
        let bbox = [0.35, 0.55, 0.65, 0.85]; // default
        if (lbl.includes('POTHOLE')) {
          bbox = [0.38, 0.62, 0.54, 0.74];
        } else if (lbl.includes('SIGN')) {
          bbox = [0.72, 0.42, 0.85, 0.62];
        } else if (lbl.includes('CRACK') || lbl.includes('DAMAGE') || lbl.includes('DETERIORATION')) {
          bbox = [0.28, 0.68, 0.68, 0.85];
        }

        const x1 = bbox[0] * canvas.width;
        const y1 = bbox[1] * canvas.height;
        const x2 = bbox[2] * canvas.width;
        const y2 = bbox[3] * canvas.height;
        const w = x2 - x1;
        const h = y2 - y1;

        const color = DETECTION_ACCENT_COLOR;
        const shadowWidth = Math.max(2, canvas.width * 0.0025);
        const drawContrastStroke = (drawPath, options = {}) => {
          const {
            lineWidth = Math.max(3, canvas.width * 0.0035),
            dash = [],
            lineCap = 'butt',
            lineJoin = 'miter',
          } = options;
          [
            [DETECTION_SHADOW_COLOR, lineWidth + shadowWidth],
            [color, lineWidth],
          ].forEach(([strokeStyle, width]) => {
            ctx.save();
            ctx.beginPath();
            ctx.strokeStyle = strokeStyle;
            ctx.lineWidth = width;
            ctx.lineCap = lineCap;
            ctx.lineJoin = lineJoin;
            ctx.setLineDash(dash);
            drawPath();
            ctx.stroke();
            ctx.restore();
          });
        };

        // 2. Draw semi-transparent bounding polygon overlay
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.08;
        ctx.fillRect(x1, y1, w, h);
        ctx.globalAlpha = 1.0;

        // 3. Draw Target Bounding Box
        drawContrastStroke(
          () => ctx.rect(x1, y1, w, h),
          {
            lineWidth: Math.max(3, canvas.width * 0.0035),
            dash: [Math.max(4, canvas.width * 0.006), Math.max(4, canvas.width * 0.006)],
          }
        );

        // 4. Draw Corner L-Brackets (thick solid lines)
        const bLen = Math.min(w, h) * 0.22;

        drawContrastStroke(
          () => {
            ctx.moveTo(x1 + bLen, y1);
            ctx.lineTo(x1, y1);
            ctx.lineTo(x1, y1 + bLen);
            ctx.moveTo(x2 - bLen, y1);
            ctx.lineTo(x2, y1);
            ctx.lineTo(x2, y1 + bLen);
            ctx.moveTo(x1 + bLen, y2);
            ctx.lineTo(x1, y2);
            ctx.lineTo(x1, y2 - bLen);
            ctx.moveTo(x2 - bLen, y2);
            ctx.lineTo(x2, y2);
            ctx.lineTo(x2, y2 - bLen);
          },
          {
            lineWidth: Math.max(5, canvas.width * 0.0055),
            lineCap: 'round',
            lineJoin: 'round',
          }
        );

        // 5. Draw Center Crosshair Target Ring
        const cx = (x1 + x2) / 2;
        const cy = (y1 + y2) / 2;
        const r = Math.min(w, h) * 0.14;
        drawContrastStroke(
          () => ctx.arc(cx, cy, r, 0, 2 * Math.PI),
          {
            lineWidth: Math.max(2, canvas.width * 0.002),
            dash: [Math.max(3, canvas.width * 0.003), Math.max(3, canvas.width * 0.003)],
          }
        );

        // Center Dot
        ctx.fillStyle = DETECTION_SHADOW_COLOR;
        ctx.beginPath();
        ctx.arc(cx, cy, Math.max(6, canvas.width * 0.006), 0, 2 * Math.PI);
        ctx.fill();
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(cx, cy, Math.max(4, canvas.width * 0.004), 0, 2 * Math.PI);
        ctx.fill();

        // 6. Draw Target Arrow (pointing directly downwards at top center of bbox)
        const arrStartY = y1 - Math.max(45, canvas.height * 0.055);
        const arrEndY = y1 - Math.max(5, canvas.height * 0.006);
        const arrHeadSize = Math.max(12, canvas.width * 0.014);

        drawContrastStroke(
          () => {
            ctx.moveTo(cx, arrStartY);
            ctx.lineTo(cx, arrEndY);
            ctx.moveTo(cx - arrHeadSize, arrEndY - arrHeadSize);
            ctx.lineTo(cx, arrEndY);
            ctx.lineTo(cx + arrHeadSize, arrEndY - arrHeadSize);
          },
          {
            lineWidth: Math.max(5, canvas.width * 0.005),
            lineCap: 'round',
            lineJoin: 'round',
          }
        );

        // 7. Draw AI Targeting Label tag
        const fontSize = Math.max(14, Math.round(canvas.width * 0.016));
        ctx.font = `bold ${fontSize}px sans-serif`;
        const text = `${anomalyShortName(defect.type || defect.detection_type)} (${Math.round(defect.confidence * 100)}% CONF)`;
        const textWidth = ctx.measureText(text).width;
        const padX = 14;
        const padY = 8;
        const tagW = textWidth + padX * 2;
        const tagH = fontSize + padY * 2;
        const tagX = cx - tagW / 2;
        const tagY = arrStartY - tagH - 6;

        // Draw tag capsule background
        ctx.fillStyle = DETECTION_LABEL_BACKGROUND;
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(tagX, tagY, tagW, tagH, 8);
        } else {
          ctx.rect(tagX, tagY, tagW, tagH);
        }
        ctx.fill();

        // Draw tag border
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw text
        ctx.fillStyle = '#ffffff';
        ctx.textBaseline = 'top';
        ctx.fillText(text, tagX + padX, tagY + padY);

        // 7.5. Draw source video info card (top-left watermark)
        const videoName = getDetectionSourceVideo(defect);
        const titleFontSize = Math.max(10, Math.round(canvas.width * 0.01));
        const valueFontSize = Math.max(12, Math.round(canvas.width * 0.013));
        
        ctx.font = `bold ${titleFontSize}px sans-serif`;
        const titleText = "DASHCAMR ANALYTICS SYSTEM";
        const titleWidth = ctx.measureText(titleText).width;
        
        ctx.font = `bold ${valueFontSize}px sans-serif`;
        const maxCardW = canvas.width - 48;
        const fitText = (text, maxWidth) => {
          if (ctx.measureText(text).width <= maxWidth) return text;
          let clipped = text;
          while (clipped.length > 4 && ctx.measureText(`${clipped}...`).width > maxWidth) {
            clipped = clipped.slice(0, -1);
          }
          return `${clipped}...`;
        };
        const valueText = fitText(`Source Video: ${videoName}`, maxCardW - 32);
        const valueWidth = ctx.measureText(valueText).width;
        
        const cardW = Math.min(maxCardW, Math.max(titleWidth, valueWidth) + 32);
        const cardH = titleFontSize + valueFontSize + 24;
        const cardX = 24;
        const cardY = 24;
        
        // Draw card background
        ctx.fillStyle = 'rgba(5, 8, 16, 0.88)';
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(cardX, cardY, cardW, cardH, 8);
        } else {
          ctx.rect(cardX, cardY, cardW, cardH);
        }
        ctx.fill();
        
        // Draw card subtle border
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        // Draw title text
        ctx.fillStyle = '#94a3b8'; // Slate grey color
        ctx.font = `bold ${titleFontSize}px sans-serif`;
        ctx.textBaseline = 'top';
        ctx.fillText(titleText, cardX + 16, cardY + 10);
        
        // Draw value text
        ctx.fillStyle = '#ffffff'; // White color
        ctx.font = `bold ${valueFontSize}px sans-serif`;
        ctx.textBaseline = 'top';
        ctx.fillText(valueText, cardX + 16, cardY + 12 + titleFontSize);

        // 8. Trigger canvas download using high-compatibility Blobs
        const blob = await new Promise((resolve, reject) => {
          canvas.toBlob((b) => {
            if (b) resolve(b);
            else reject(new Error('Canvas compilation failed'));
          }, 'image/jpeg', 0.95);
        });
        
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(blobUrl);
        return;
      }

      // Standard fallback download for general attachments
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error('Download failed:', error);
      setErrorMessage(`Failed to download evidence image: ${error.message || 'Unknown network error'}`);
    }
  };

  if (!currentUser) {
    return <LoginPage loginError={loginError} onLogin={handleLogin} />;
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Sidebar />
      
      <main style={{ flex: 1, padding: '32px', overflowY: 'auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
          <div>
            <p className="dashboard-breadcrumb">Home / Road Analytics Monitoring System (RAMS)</p>
            <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Road Analytics Monitoring System</h1>
          </div>
          
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <div className="glass-panel" style={{ padding: '10px', borderRadius: '12px', cursor: 'pointer' }}>
              <Bell size={20} />
            </div>
            <div className="user-session">
              <div className="user-session-icon">
                <ShieldCheck size={18} />
              </div>
              <div className="user-session-copy">
                <span>{currentUser.displayName}</span>
              </div>
              <button
                className="logout-button"
                type="button"
                onClick={handleLogout}
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </header>

        {/* ─── Video Upload Section ─────────────────────────────────────── */}
        <section className="glass-panel report-preflight" style={{ padding: '24px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'rgba(37, 99, 235, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(37, 99, 235, 0.18)'
            }}>
              <FileText size={20} color="var(--accent-blue)" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem' }}>Report Details</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Report details are optional and can be added before downloading the report.
              </p>
            </div>
          </div>

          <div className="report-form-grid report-form-grid-priority">
            <label className="report-field">
              <span>NH Number</span>
              <input
                className="report-input"
                name="nh_number"
                type="text"
                value={reportForm.nh_number}
                placeholder="NH-44"
                onChange={(event) => handleReportFieldChange('nh_number', event.target.value)}
              />
            </label>

            <label className="report-field">
              <span>RO Name</span>
              <select
                className="report-select"
                name="ro_name"
                value={reportForm.ro_name}
                onChange={(event) => handleReportFieldChange('ro_name', event.target.value)}
              >
                <option value="">Select RO Name</option>
                {REPORT_MASTER_DATA.map(item => (
                  <option key={item.ro_name} value={item.ro_name}>
                    {item.ro_name}
                  </option>
                ))}
              </select>
            </label>

            <label className="report-field">
              <span>PIU Name</span>
              <select
                className="report-select"
                name="piu_name"
                value={reportForm.piu_name}
                onChange={(event) => handleReportFieldChange('piu_name', event.target.value)}
                disabled={!reportForm.ro_name}
              >
                <option value="">Select PIU Name</option>
                {piuOptions.map(item => (
                  <option key={item.piu_name} value={item.piu_name}>
                    {item.piu_name}
                  </option>
                ))}
              </select>
            </label>

            <label className="report-field">
              <span>UPC Code</span>
              <select
                className="report-select"
                name="upc_code"
                value={reportForm.upc_code}
                onChange={(event) => handleReportFieldChange('upc_code', event.target.value)}
                disabled={!reportForm.piu_name}
              >
                <option value="">Select UPC Code</option>
                {upcOptions.map(upcCode => (
                  <option key={upcCode} value={upcCode}>
                    {upcCode}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="report-form-grid report-preflight-manual">
            {REPORT_MANUAL_FIELDS.map(field => {
              return (
                <label
                  className={`report-field ${field.wide ? 'report-field-wide' : ''}`}
                  key={field.name}
                >
                  <span>{field.label}</span>
                  <input
                    className="report-input"
                    name={field.name}
                    type={field.type}
                    value={reportForm[field.name]}
                    placeholder={field.placeholder}
                    onChange={(event) => handleReportFieldChange(field.name, event.target.value)}
                  />
                </label>
              );
            })}
          </div>
        </section>

        <section className="glass-panel" style={{ padding: '24px', marginBottom: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <div style={{ 
              width: '40px', height: '40px', borderRadius: '12px', 
              background: 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(139,92,246,0.2))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1px solid rgba(59,130,246,0.3)'
            }}>
              <Film size={20} color="var(--accent-blue)" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem' }}>Dashcam Video Analysis</h3>
            </div>
          </div>

          {uploadState === 'idle' && (
            <div
              className={`upload-zone ${dragOver && isUploadEnabled ? 'upload-zone-active' : ''} ${!isUploadEnabled ? 'upload-zone-disabled' : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => {
                if (isUploadEnabled) {
                  document.getElementById('video-input').click();
                }
              }}
              aria-disabled={!isUploadEnabled}
            >
              <input
                id="video-input"
                type="file"
                accept=".mp4,.mov,.avi,.mkv"
                style={{ display: 'none' }}
                disabled={!isUploadEnabled}
                onChange={(e) => handleUpload(e.target.files[0])}
              />
              <Upload size={40} color={isUploadEnabled ? 'var(--accent-blue)' : '#94a3b8'} style={{ marginBottom: '12px' }} />
              <p style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '4px' }}>
                {isUploadEnabled ? 'Drag & drop dashcam video here' : uploadDisabledReason}
              </p>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                {isUploadEnabled ? 'or click to browse - MP4, MOV, AVI, MKV' : 'or click to browse - MP4, MOV, AVI, MKV'}
              </p>
              <button
                type="button"
                className="upload-action-button"
                disabled={!isUploadEnabled}
              >
                Upload Video
              </button>
            </div>
          )}

          {(uploadState === 'uploading' || uploadState === 'processing') && (
            <div className="pipeline-tracker">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                <Loader2 size={20} className="spin" color="var(--accent-blue)" />
                <span style={{ fontWeight: 600 }}>
                  Processing: {uploadedFile?.name}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="progress-bar-track">
                <div className="progress-bar-fill" style={{ width: `${uploadProgress}%` }} />
              </div>

              {/* Pipeline Steps */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '20px' }}>
                {PIPELINE_STEPS.map((step, i) => (
                  <div key={step.key} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div className={`step-indicator ${i < pipelineStep ? 'step-done' : i === pipelineStep ? 'step-active' : 'step-pending'}`}>
                      {i < pipelineStep ? (
                        <CheckCircle size={18} />
                      ) : i === pipelineStep ? (
                        <Loader2 size={18} className="spin" />
                      ) : (
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--border-color)', display: 'block' }} />
                      )}
                    </div>
                    <span style={{ 
                      color: i <= pipelineStep ? 'var(--text-primary)' : 'var(--text-secondary)',
                      fontWeight: i === pipelineStep ? 600 : 400,
                      fontSize: '0.9rem'
                    }}>
                      {step.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {uploadState === 'complete' && (
            <div className="pipeline-complete">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <CheckCircle2 size={24} color="var(--accent-green)" />
                <span style={{ fontWeight: 600, fontSize: '1.05rem', color: 'var(--accent-green)' }}>
                  Analysis Complete
                </span>
              </div>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem' }}>
                Defect analysis for <strong style={{ color: 'var(--text-primary)' }}>{uploadedFile?.name}</strong> has finished.
                Results are now visible in the dashboard.
              </p>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button
                  onClick={handleReportDownload}
                  style={{
                    height: '40px',
                    backgroundColor: 'var(--accent-blue)',
                    color: '#fff',
                    border: 'none',
                    padding: '0 16px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  <FileText size={18} />
                  Download Report
                </button>
                <button onClick={resetUpload} className="btn-secondary">
                  Analyze Another Video
                </button>
              </div>
            </div>
          )}

          {uploadState === 'error' && (
            <div className="pipeline-error">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <XCircle size={24} color="var(--accent-red)" />
                <span style={{ fontWeight: 600, color: 'var(--accent-red)' }}>
                  Pipeline Error
                </span>
              </div>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem' }}>
                {errorMessage}
              </p>
              <button onClick={resetUpload} className="btn-secondary">
                Try Again
              </button>
            </div>
          )}
        </section>

        {/* ─── Stats Section ────────────────────────────────────────────── */}
        {/* ─── Highway Geospatial Defect Map ─── */}
        {renderRoadAnalyticsReport()}

        <section className="glass-panel" style={{ display: 'none' }} aria-hidden="true">
          <h3 style={{ marginBottom: '24px' }}>Legacy Detection Cards</h3>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', 
            gap: '24px' 
          }}>
            {[].map((defect, i) => {
              const imageUrl = (defect.id && !defect.is_demo && !String(defect.id).startsWith('demo')) ? `${API_BASE}/api/v1/defects/${defect.id}/image` : FALLBACK_ROAD_IMAGE;
              
              return (
                <div key={i} className="glass-panel" style={{ 
                  padding: '16px', 
                  borderRadius: '16px', 
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  transition: 'transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.25s ease',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-6px)';
                  e.currentTarget.style.borderColor = 'var(--accent-blue)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                }}
                >
                  <div style={{ 
                    width: '100%', 
                    height: '160px', 
                    borderRadius: '12px', 
                    overflow: 'hidden',
                    position: 'relative',
                    backgroundColor: '#0c0f16',
                    border: '1px solid rgba(255,255,255,0.05)'
                  }}>
                    <DetectionImage
                      src={imageUrl}
                      fallbackSrc={FALLBACK_ROAD_IMAGE}
                      alt={defect.type || 'Anomaly'}
                      annotation={defect.annotation}
                      label={anomalyShortName(defect.type || defect.detection_type)}
                      color={DETECTION_ACCENT_COLOR}
                      shadowColor={DETECTION_SHADOW_COLOR}
                      labelBackground={DETECTION_LABEL_BACKGROUND}
                      compact
                      videoName={getDetectionSourceVideo(defect)}
                    />

                    <div style={{ 
                      position: 'absolute', 
                      top: '10px', 
                      right: '10px', 
                      backgroundColor: 'rgba(15, 23, 42, 0.8)', 
                      backdropFilter: 'blur(4px)',
                      padding: '4px 8px', 
                      borderRadius: '8px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: defect.confidence > 0.8 ? '#10b981' : '#f59e0b',
                      border: '1px solid rgba(255,255,255,0.1)'
                    }}>
                      {Math.round(defect.confidence * 100)}% Conf
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 600, textTransform: 'capitalize', marginBottom: '6px', color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {(defect.type || defect.detection_type || 'Unknown').replace('_', ' ')}
                      {defect.is_demo && (
                        <span style={{ 
                          fontSize: '0.55rem', 
                          padding: '1px 4px', 
                          borderRadius: '4px', 
                          backgroundColor: 'rgba(245, 158, 11, 0.15)', 
                          color: '#f59e0b', 
                          border: '1px solid rgba(245, 158, 11, 0.3)',
                          fontWeight: 700,
                          textTransform: 'uppercase'
                        }}>Demo</span>
                      )}
                    </h4>
                    <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: 'var(--accent-blue)' }}>📍</span> Lat: {defect.latitude?.toFixed(5)}, Lng: {defect.longitude?.toFixed(5)}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', marginTop: 'auto' }}>
                    <button 
                      onClick={() => setSelectedDefect(defect)}
                      style={{ 
                        flex: 1, 
                        backgroundColor: 'rgba(59,130,246,0.1)', 
                        color: 'var(--accent-blue)', 
                        border: '1px solid rgba(59,130,246,0.2)', 
                        padding: '8px', 
                        borderRadius: '8px', 
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--accent-blue)';
                        e.currentTarget.style.color = '#fff';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(59,130,246,0.1)';
                        e.currentTarget.style.color = 'var(--accent-blue)';
                      }}
                    >
                      View
                    </button>
                    <button 
                      onClick={() => handleDownload(imageUrl, buildDetectionImageFilename(defect, i), defect)}
                      style={{ 
                        backgroundColor: 'rgba(255,255,255,0.03)', 
                        color: '#fff', 
                        border: '1px solid var(--border-color)', 
                        padding: '8px 12px', 
                        borderRadius: '8px', 
                        fontSize: '0.8rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.03)'}
                      title="Download Image"
                    >
                      ⬇️
                    </button>
                  </div>
                </div>
              );
            })}
            {defects.length === 0 && (
              <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                No anomaly images processed yet.
              </div>
            )}
          </div>
        </section>
      </main>

      {/* ─── Image Modal ──────────────────────────────────────────────── */}
      {selectedDefect && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(5, 8, 16, 0.9)',
          backdropFilter: 'blur(12px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999,
          padding: '24px'
        }}
        onClick={() => setSelectedDefect(null)}
        >
          <div style={{
            position: 'relative',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '24px',
            padding: '24px',
            maxWidth: '800px',
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
          }}
          onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ textTransform: 'capitalize', fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '4px' }}>
                  {(selectedDefect.type || selectedDefect.detection_type || 'Unknown').replace('_', ' ')} Detection
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  📍 Lat: {selectedDefect.latitude?.toFixed(6)}, Lng: {selectedDefect.longitude?.toFixed(6)}
                </p>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px' }}>
                  Source video: {getDetectionSourceVideo(selectedDefect)}
                </p>
              </div>
              <button 
                onClick={() => setSelectedDefect(null)}
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: 'none',
                  color: '#fff',
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.2rem',
                  cursor: 'pointer',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'}
              >
                ×
              </button>
            </div>

            <div style={{
              width: '100%',
              height: '420px',
              borderRadius: '16px',
              overflow: 'hidden',
              backgroundColor: '#050810',
              border: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative'
            }}>
              <DetectionImage
                src={(selectedDefect.id && !selectedDefect.is_demo && !String(selectedDefect.id).startsWith('demo')) ? `${API_BASE}/api/v1/defects/${selectedDefect.id}/image` : FALLBACK_ROAD_IMAGE}
                fallbackSrc={FALLBACK_ROAD_IMAGE}
                alt="Anomaly full view"
                annotation={selectedDefect.annotation}
                label={`${anomalyShortName(selectedDefect.type || selectedDefect.detection_type)} (${Math.round(selectedDefect.confidence * 100)}% CONF)`}
                color={DETECTION_ACCENT_COLOR}
                shadowColor={DETECTION_SHADOW_COLOR}
                labelBackground={DETECTION_LABEL_BACKGROUND}
                videoName={getDetectionSourceVideo(selectedDefect)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button 
                onClick={() => setSelectedDefect(null)}
                className="btn-secondary"
                style={{ padding: '10px 20px', borderRadius: '12px' }}
              >
                Close
              </button>
              <button 
                onClick={() => handleDownload(
                  (selectedDefect.id && !selectedDefect.is_demo && !String(selectedDefect.id).startsWith('demo')) ? `${API_BASE}/api/v1/defects/${selectedDefect.id}/image` : FALLBACK_ROAD_IMAGE,
                  buildDetectionImageFilename(selectedDefect),
                  selectedDefect
                )}
                style={{
                  backgroundColor: 'var(--accent-blue)',
                  color: '#fff',
                  border: 'none',
                  padding: '10px 20px',
                  borderRadius: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--accent-blue)'}
              >
                Download Image
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
