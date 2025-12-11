import { useState, useCallback, useEffect, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { 
  Upload, 
  FileText, 
  Copy, 
  Download, 
  Trash2, 
  Settings, 
  Loader2,
  CheckCircle,
  AlertCircle,
  Image,
  FileType,
  Sparkles,
  BarChart3,
  LogIn,
  LogOut,
  Users,
  Search,
  Play,
  RefreshCw,
  Hospital,
  Heart,
  Calendar,
  User,
  ChevronRight,
  Table,
  X,
  FileSpreadsheet
} from 'lucide-react'

const API_URL = '/api'

const languages = [
  { code: 'korean', name: '한국어' },
  { code: 'en', name: '영어' },
  { code: 'japan', name: '일본어' },
  { code: 'ch', name: '중국어(간체)' },
  { code: 'chinese_cht', name: '중국어(번체)' },
]

// 탭 컴포넌트
function TabButton({ active, onClick, children, icon: Icon }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-5 py-3 rounded-xl font-medium transition-all duration-300 ${
        active
          ? 'bg-gradient-to-r from-violet-600 to-purple-600 text-white glow-purple'
          : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50 hover:text-white'
      }`}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {children}
    </button>
  )
}

// 파일 OCR 컴포넌트
function FileOCRTab({ language, confidenceThreshold, showConfidence }) {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  const onDrop = useCallback((acceptedFiles) => {
    const selectedFile = acceptedFiles[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError(null)
      setResult(null)
      
      if (selectedFile.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = (e) => setPreview(e.target.result)
        reader.readAsDataURL(selectedFile)
      } else {
        setPreview(null)
      }
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'],
      'application/pdf': ['.pdf']
    },
    multiple: false
  })

  const handleOCR = async () => {
    if (!file) return

    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('confidence_threshold', confidenceThreshold)
    formData.append('include_confidence', showConfidence)
    formData.append('language', language)

    try {
      const response = await axios.post(`${API_URL}/ocr`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      if (response.data.success) {
        setResult(response.data)
      } else {
        setError(response.data.error || 'OCR 처리 중 오류가 발생했습니다.')
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '서버 연결에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    if (result?.text) {
      await navigator.clipboard.writeText(result.text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownload = () => {
    if (result?.text) {
      const blob = new Blob([result.text], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ocr_result_${Date.now()}.txt`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleClear = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
    setError(null)
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left Panel - Upload & Preview */}
      <div className="space-y-6">
        <div
          {...getRootProps()}
          className={`glass rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${
            isDragActive 
              ? 'border-2 border-violet-500 glow-purple scale-[1.02]' 
              : 'border-2 border-dashed border-slate-600 hover:border-violet-500/50'
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-4">
            <div className={`p-4 rounded-2xl transition-all ${
              isDragActive ? 'bg-violet-500/20' : 'bg-slate-800/50'
            }`}>
              <Upload className={`w-10 h-10 ${isDragActive ? 'text-violet-400' : 'text-slate-400'}`} />
            </div>
            <div>
              <p className="text-lg font-medium text-white mb-1">
                {isDragActive ? '여기에 놓으세요!' : '파일을 드래그하거나 클릭하세요'}
              </p>
              <p className="text-sm text-slate-400">
                PNG, JPG, JPEG, PDF 등 지원
              </p>
            </div>
          </div>
        </div>

        {file && (
          <div className="glass rounded-2xl p-6 animate-fade-in">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                {file.type.startsWith('image/') ? (
                  <Image className="w-8 h-8 text-violet-400" />
                ) : (
                  <FileType className="w-8 h-8 text-violet-400" />
                )}
                <div>
                  <p className="font-medium text-white truncate max-w-[200px]">
                    {file.name}
                  </p>
                  <p className="text-sm text-slate-400">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>
              <button
                onClick={handleClear}
                className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>

            {preview && (
              <div className="relative rounded-xl overflow-hidden bg-slate-900/50">
                <img
                  src={preview}
                  alt="Preview"
                  className="w-full max-h-[300px] object-contain"
                />
              </div>
            )}

            <button
              onClick={handleOCR}
              disabled={loading}
              className="w-full mt-4 py-4 px-6 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 glow-purple"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  OCR 처리 중...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  텍스트 추출하기
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Right Panel - Results */}
      <div className="glass rounded-2xl p-6 min-h-[400px] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-violet-400" />
            추출 결과
          </h2>
          
          {result && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="p-2 rounded-lg text-slate-400 hover:text-violet-400 hover:bg-violet-500/10 transition-all"
                title="복사"
              >
                {copied ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <Copy className="w-5 h-5" />
                )}
              </button>
              <button
                onClick={handleDownload}
                className="p-2 rounded-lg text-slate-400 hover:text-violet-400 hover:bg-violet-500/10 transition-all"
                title="다운로드"
              >
                <Download className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 mb-4 animate-fade-in">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-auto">
          {result ? (
            <div className="space-y-4 animate-fade-in">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-800/50">
                  <p className="text-xs text-slate-400 mb-1">줄 수</p>
                  <p className="text-lg font-semibold text-white">
                    {result.statistics?.total_lines || 0}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-800/50">
                  <p className="text-xs text-slate-400 mb-1">글자 수</p>
                  <p className="text-lg font-semibold text-white">
                    {result.statistics?.total_characters || 0}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-800/50">
                  <p className="text-xs text-slate-400 mb-1">페이지</p>
                  <p className="text-lg font-semibold text-white">
                    {result.statistics?.pages || 1}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-800/50">
                  <p className="text-xs text-slate-400 mb-1">평균 신뢰도</p>
                  <p className="text-lg font-semibold text-white">
                    {((result.statistics?.average_confidence || 0) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-700/50">
                <pre className="whitespace-pre-wrap text-sm text-slate-200 font-mono leading-relaxed max-h-[400px] overflow-auto">
                  {result.text || '(인식된 텍스트가 없습니다)'}
                </pre>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center py-12">
              <div className="p-4 rounded-2xl bg-slate-800/30 mb-4">
                <BarChart3 className="w-12 h-12 text-slate-600" />
              </div>
              <p className="text-slate-400 mb-2">아직 결과가 없습니다</p>
              <p className="text-sm text-slate-500">
                이미지를 업로드하고 텍스트를 추출해보세요
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// 데이터 추출 모달 컴포넌트
function ExtractionModal({ isOpen, onClose, ocrResults, startDate, endDate, dateRangeMode, patients }) {
  const [extractedData, setExtractedData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 날짜 포맷 변환: "2025-12-11" -> "25.12.11" 또는 "10:52:53 2025-12-10" -> "25.12.10"
  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    
    // DCAS 형식: "10:52:53 2025-12-10" -> 날짜 부분만 추출
    if (dateStr.includes(' ')) {
      const parts = dateStr.split(' ')
      dateStr = parts[parts.length - 1] // 마지막 부분 (날짜)
    }
    
    const parts = dateStr.split('-')
    if (parts.length !== 3) return dateStr
    const year = parts[0].slice(-2) // 마지막 2자리
    const month = parts[1]
    const day = parts[2]
    return `${year}.${month}.${day}`
  }

  // 모달이 열릴 때 데이터 추출 실행
  useEffect(() => {
    if (isOpen && ocrResults.length > 0) {
      extractData()
    }
  }, [isOpen, ocrResults])

  // OCR 텍스트에서 데이터 추출
  const extractData = async () => {
    setLoading(true)
    setError('')
    
    try {
      // 각 결과에서 데이터 추출
      const extracted = ocrResults.map((result) => {
        const text = result.text || ''
        
        // 환자 정보에서 성별 가져오기
        const patientInfo = patients?.find(p => p.patient_id === result.patient_id)
        let gender = ''
        if (patientInfo?.gender) {
          // "M" 또는 "F" 형태로 변환 (이미 M/F 형식이면 그대로 사용)
          const g = patientInfo.gender.toUpperCase()
          if (g === 'M' || g === 'MALE' || g === '남' || g === '남자') {
            gender = 'M'
          } else if (g === 'F' || g === 'FEMALE' || g === '여' || g === '여자') {
            gender = 'F'
          } else {
            gender = g.charAt(0) // 첫 글자만 사용
          }
        }
        
        // DAP 추출 (숫자.숫자 Gy·cm2 형식 찾기)
        let dap = ''
        const dapMatch = text.match(/([\d.]+)\s*Gy[·\.]?cm2?/i)
        if (dapMatch) {
          const dapValue = parseFloat(dapMatch[1])
          dap = String(Math.round(dapValue * 1000))
        }
        
        // Air Kerma 추출 (숫자 mGy 형식)
        let ak = ''
        const akPatterns = [
          /([\d.]+)\s*mGy\s*[\n\r]*.*Total\s*Air\s*Kerma/is,
          /Total\s*Air\s*Kerma.*?([\d.]+)\s*mGy/is,
          /([\d]+)\s*mGy/i
        ]
        for (const pattern of akPatterns) {
          const match = text.match(pattern)
          if (match) {
            ak = match[1].split('.')[0]
            break
          }
        }
        
        // Fluoro Time 추출 (시:분:초 형식)
        let fluoroTime = ''
        const timePatterns = [
          /([\d]{1,2}:[\d]{2}:[\d]{2})\s*[\n\r]*.*Total\s*Fluoroscopy\s*Time/is,
          /Total\s*Fluoroscopy\s*Time.*?([\d]{1,2}:[\d]{2}:[\d]{2})/is,
          /([\d]{1,2}:[\d]{2}:[\d]{2})/
        ]
        for (const pattern of timePatterns) {
          const match = text.match(pattern)
          if (match) {
            fluoroTime = match[1]
            break
          }
        }
        
        // Exposure Series 추출
        let exposureSeries = ''
        const seriesMatch = text.match(/([\d]+)\s*[\n\r]*\s*Exposure\s*Series/i) ||
                           text.match(/Exposure\s*Series\s*[\n\r]*\s*([\d]+)/i)
        if (seriesMatch) {
          exposureSeries = seriesMatch[1]
        }
        
        // Exposure Images 추출
        let exposureImages = ''
        const imagesMatch = text.match(/([\d]+)\s*[\n\r]*\s*Exposure\s*Images/i) ||
                           text.match(/Exposure\s*Images\s*[\n\r]*\s*([\d]+)/i)
        if (imagesMatch) {
          exposureImages = imagesMatch[1]
        }
        
        // RUN 조합
        const run = exposureSeries && exposureImages ? `${exposureSeries}/${exposureImages}` : ''
        
        // ROOM 결정 (15 cm from isocenter 텍스트 확인)
        const hasIRP = /15\s*cm\s*(from\s*the\s*)?isocenter/i.test(text)
        const room = hasIRP ? '2' : '1'
        
        // 환자의 실제 검사 날짜 사용 (study_date가 있으면)
        let patientDate = ''
        if (patientInfo?.study_date) {
          patientDate = formatDate(patientInfo.study_date)
        } else if (!dateRangeMode) {
          patientDate = formatDate(startDate)
        }
        
        return {
          patient_id: result.patient_id || '',
          patient_name: result.patient_name || '',
          gender,
          date: patientDate,
          dap,
          ak,
          fluoro_time: fluoroTime,
          col1: '0',
          col2: '0',
          col3: '0',
          run,
          room
        }
      })
      
      setExtractedData(extracted)
    } catch (err) {
      setError('데이터 추출 중 오류가 발생했습니다.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // 개별 데이터 수정 핸들러
  const updateField = (index, field, value) => {
    setExtractedData(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
  }

  // CSV 다운로드
  const downloadCSV = () => {
    if (extractedData.length === 0) return
    
    // CSV 헤더
    const headers = ['날짜', '등록번호', '성별', 'DAP', 'AK', 'Fluoro Time', '0', '0', '0', 'RUN', 'ROOM']
    
    // CSV 데이터 행
    const rows = extractedData.map(data => [
      data.date,
      data.patient_id,
      data.gender,
      data.dap,
      data.ak,
      data.fluoro_time,
      data.col1,
      data.col2,
      data.col3,
      data.run,
      data.room
    ])
    
    // CSV 문자열 생성 (BOM 추가로 한글 인코딩 문제 해결)
    const BOM = '\uFEFF'
    const csvContent = BOM + [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n')
    
    // 다운로드
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // 기간 선택 모드일 경우 파일명에 시작일~종료일 포함
    const dateRange = dateRangeMode && endDate !== startDate 
      ? `${startDate}_to_${endDate}` 
      : startDate
    a.download = `dose_report_${dateRange}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  // 클립보드 복사 (탭 구분)
  const copyToClipboard = () => {
    if (extractedData.length === 0) return
    
    const rows = extractedData.map(data => 
      [data.date, data.patient_id, data.gender, data.dap, data.ak, data.fluoro_time, 
       data.col1, data.col2, data.col3, data.run, data.room].join('\t')
    )
    
    navigator.clipboard.writeText(rows.join('\n'))
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-2xl border border-slate-700 max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* 모달 헤더 */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="font-semibold text-white">데이터 추출</h3>
              <p className="text-xs text-slate-400">
                {dateRangeMode 
                  ? `기간: ${startDate} ~ ${endDate} (날짜를 직접 입력해주세요)` 
                  : `날짜: ${startDate}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={copyToClipboard}
              className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm flex items-center gap-2 transition-all"
              title="클립보드에 복사"
            >
              <Copy className="w-4 h-4" />
              복사
            </button>
            <button
              onClick={downloadCSV}
              className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm flex items-center gap-2 transition-all"
            >
              <Download className="w-4 h-4" />
              CSV 다운로드
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-slate-700/50 text-slate-400 hover:text-white transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        {/* 모달 본문 */}
        <div className="p-4 overflow-auto flex-1">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 className="w-10 h-10 text-emerald-400 animate-spin mb-4" />
              <p className="text-slate-400">데이터 추출 중...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-20">
              <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
              <p className="text-red-400">{error}</p>
            </div>
          ) : extractedData.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Table className="w-12 h-12 text-slate-600 mb-4" />
              <p className="text-slate-400">추출할 데이터가 없습니다</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">환자</th>
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">날짜</th>
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">등록번호</th>
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">성별</th>
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">DAP</th>
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">AK</th>
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">Fluoro Time</th>
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">RUN</th>
                    <th className="text-left p-2 text-slate-400 font-medium whitespace-nowrap">ROOM</th>
                  </tr>
                </thead>
                <tbody>
                  {extractedData.map((data, index) => (
                    <tr key={index} className="border-b border-slate-800 hover:bg-slate-800/50">
                      <td className="p-2 text-white whitespace-nowrap">
                        <div>
                          <div className="font-medium">{data.patient_name || '-'}</div>
                          <div className="text-xs text-slate-500">{data.patient_id}</div>
                        </div>
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={data.date}
                          onChange={(e) => updateField(index, 'date', e.target.value)}
                          placeholder="25.12.11"
                          className="px-2 py-1 w-24 rounded bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={data.patient_id}
                          onChange={(e) => updateField(index, 'patient_id', e.target.value)}
                          className="px-2 py-1 w-24 rounded bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                      </td>
                      <td className="p-2">
                        <select
                          value={data.gender}
                          onChange={(e) => updateField(index, 'gender', e.target.value)}
                          className="px-2 py-1 w-16 rounded bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        >
                          <option value="">-</option>
                          <option value="M">M</option>
                          <option value="F">F</option>
                        </select>
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={data.dap}
                          onChange={(e) => updateField(index, 'dap', e.target.value)}
                          className="px-2 py-1 w-20 rounded bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                          placeholder="DAP"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={data.ak}
                          onChange={(e) => updateField(index, 'ak', e.target.value)}
                          className="px-2 py-1 w-16 rounded bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                          placeholder="AK"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={data.fluoro_time}
                          onChange={(e) => updateField(index, 'fluoro_time', e.target.value)}
                          className="px-2 py-1 w-20 rounded bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                          placeholder="0:00:00"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={data.run}
                          onChange={(e) => updateField(index, 'run', e.target.value)}
                          className="px-2 py-1 w-20 rounded bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                          placeholder="0/0"
                        />
                      </td>
                      <td className="p-2">
                        <select
                          value={data.room}
                          onChange={(e) => updateField(index, 'room', e.target.value)}
                          className="px-2 py-1 w-14 rounded bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        >
                          <option value="1">1</option>
                          <option value="2">2</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        
        {/* CSV 미리보기 */}
        {extractedData.length > 0 && (
          <div className="p-4 border-t border-slate-700 bg-slate-800/50 flex-shrink-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-400">CSV 미리보기</span>
              <span className="text-xs text-slate-500">{extractedData.length}건</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-700 overflow-x-auto">
              <pre className="text-xs text-slate-300 font-mono whitespace-pre">
{`날짜,등록번호,성별,DAP,AK,Fluoro Time,0,0,0,RUN,ROOM
${extractedData.map(d => 
  `${d.date},${d.patient_id},${d.gender},${d.dap},${d.ak},${d.fluoro_time},0,0,0,${d.run},${d.room}`
).join('\n')}`}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


// Dcas OCR 컴포넌트
function DcasOCRTab({ language, confidenceThreshold }) {
  const [patients, setPatients] = useState([])
  const [selectedPatients, setSelectedPatients] = useState([])
  const [patientsLoading, setPatientsLoading] = useState(false)
  const [patientsError, setPatientsError] = useState('')
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0])
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0])
  const [dateRangeMode, setDateRangeMode] = useState(false) // false = 단일 날짜, true = 기간 선택
  
  const [jobId, setJobId] = useState('')
  const [jobStatus, setJobStatus] = useState(null)
  const [ocrResults, setOcrResults] = useState([])
  const [ocrLoading, setOcrLoading] = useState(false)
  const [selectedResult, setSelectedResult] = useState(null)
  
  // 미리보기 관련 state
  const [previewPatient, setPreviewPatient] = useState(null)
  const [previewImage, setPreviewImage] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')
  const [previewUrls, setPreviewUrls] = useState([])
  const [previewIndex, setPreviewIndex] = useState(0)
  const [previewTotal, setPreviewTotal] = useState(0)
  const [previewCurrentUrl, setPreviewCurrentUrl] = useState('')
  
  // 추출 모달 관련 state
  const [showExtractionModal, setShowExtractionModal] = useState(false)
  
  const pollingRef = useRef(null)

  // 환자 리스트 조회
  const fetchPatients = async () => {
    setPatientsLoading(true)
    setPatientsError('')
    
    try {
      const requestData = {
        modality: 'XA',
        start_date: startDate
      }
      
      // 기간 선택 모드일 경우 end_date 추가
      if (dateRangeMode) {
        requestData.end_date = endDate
      }
      
      const response = await axios.post(`${API_URL}/dcas/patients`, requestData)
      
      if (response.data.success) {
        setPatients(response.data.patients)
        setSelectedPatients([])
      } else {
        setPatientsError(response.data.error || '환자 리스트 조회 실패')
      }
    } catch (err) {
      setPatientsError(err.response?.data?.detail || err.message || '서버 연결 실패')
    } finally {
      setPatientsLoading(false)
    }
  }
  
  // 컴포넌트 마운트 시 자동 조회
  useEffect(() => {
    fetchPatients()
  }, [])

  // 환자 선택 토글
  const togglePatient = (patient) => {
    setSelectedPatients(prev => {
      const exists = prev.find(p => p.cine_no === patient.cine_no)
      if (exists) {
        return prev.filter(p => p.cine_no !== patient.cine_no)
      }
      return [...prev, patient]
    })
  }

  // 미리보기 요청
  const fetchPreview = async (patient, imageIndex = -1) => {
    setPreviewPatient(patient)
    setPreviewLoading(true)
    setPreviewError('')
    setPreviewImage('')
    
    try {
      const response = await axios.post(`${API_URL}/dcas/preview`, {
        cine_no: patient.cine_no,
        patient_id: patient.patient_id,
        image_index: imageIndex
      })
      
      if (response.data.success) {
        setPreviewImage(response.data.image_data)
        setPreviewUrls(response.data.image_urls || [])
        setPreviewIndex(response.data.current_index || 0)
        setPreviewTotal(response.data.total_images || 0)
        setPreviewCurrentUrl(response.data.image_url || '')
      } else {
        setPreviewError(response.data.error || '미리보기 실패')
      }
    } catch (err) {
      setPreviewError(err.response?.data?.detail || err.message || '서버 연결 실패')
    } finally {
      setPreviewLoading(false)
    }
  }

  // 이전/다음 이미지
  const prevImage = () => {
    if (previewIndex > 0 && previewPatient) {
      fetchPreview(previewPatient, previewIndex - 1)
    }
  }
  
  const nextImage = () => {
    if (previewIndex < previewTotal - 1 && previewPatient) {
      fetchPreview(previewPatient, previewIndex + 1)
    }
  }

  // 미리보기 닫기
  const closePreview = () => {
    setPreviewPatient(null)
    setPreviewImage('')
    setPreviewError('')
    setPreviewUrls([])
    setPreviewIndex(0)
    setPreviewTotal(0)
    setPreviewCurrentUrl('')
  }

  // 전체 선택/해제
  const toggleAllPatients = () => {
    if (selectedPatients.length === patients.length) {
      setSelectedPatients([])
    } else {
      setSelectedPatients([...patients])
    }
  }

  // OCR 시작
  const startOCR = async () => {
    if (selectedPatients.length === 0) return
    
    setOcrLoading(true)
    setOcrResults([])
    setSelectedResult(null)
    
    try {
      const response = await axios.post(`${API_URL}/dcas/ocr`, {
        patients: selectedPatients,
        max_workers: 4,
        language: language,
        confidence_threshold: confidenceThreshold
      })
      
      if (response.data.success) {
        setJobId(response.data.job_id)
        startPolling(response.data.job_id)
      } else {
        setOcrLoading(false)
        setPatientsError(response.data.error || 'OCR 시작 실패')
      }
    } catch (err) {
      setOcrLoading(false)
      setPatientsError(err.response?.data?.detail || err.message || '서버 연결 실패')
    }
  }

  // 상태 폴링
  const startPolling = (jid) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }
    
    pollingRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/dcas/ocr/status/${jid}`)
        
        if (response.data.success && response.data.job) {
          setJobStatus(response.data.job)
          
          if (response.data.job.results) {
            setOcrResults(response.data.job.results)
          }
          
          if (response.data.job.status === 'completed' || response.data.job.status === 'failed') {
            clearInterval(pollingRef.current)
            pollingRef.current = null
            setOcrLoading(false)
          }
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 1000)
  }

  // 컴포넌트 언마운트 시 폴링 정리
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  // 결과 전체 다운로드
  const downloadAllResults = () => {
    if (ocrResults.length === 0) return
    
    let content = ''
    ocrResults.forEach((result, index) => {
      content += `\n${'='.repeat(60)}\n`
      content += `환자 ${index + 1}: [${result.patient_id}] ${result.patient_name}\n`
      content += `${'='.repeat(60)}\n\n`
      if (result.success) {
        content += result.text || '(인식된 텍스트 없음)'
      } else {
        content += `오류: ${result.error}`
      }
      content += '\n\n'
    })
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // 기간 선택 모드일 경우 파일명에 시작일~종료일 포함
    const dateRange = dateRangeMode && endDate !== startDate 
      ? `${startDate}_to_${endDate}` 
      : startDate
    a.download = `dcas_ocr_results_${dateRange}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  // 메인 화면
  return (
    <div className="space-y-6 animate-fade-in">
      {/* 상단 컨트롤 바 */}
      <div className="glass rounded-2xl p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-wrap">
            {/* 단일/기간 선택 토글 */}
            <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-800/80">
              <button
                onClick={() => setDateRangeMode(false)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  !dateRangeMode 
                    ? 'bg-rose-500 text-white' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                단일 날짜
              </button>
              <button
                onClick={() => setDateRangeMode(true)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  dateRangeMode 
                    ? 'bg-rose-500 text-white' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                기간 선택
              </button>
            </div>
            
            {/* 날짜 선택 */}
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-400" />
              <input
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value)
                  // 단일 날짜 모드에서는 endDate도 같이 변경
                  if (!dateRangeMode) {
                    setEndDate(e.target.value)
                  }
                }}
                className="px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
              
              {dateRangeMode && (
                <>
                  <span className="text-slate-400">~</span>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    min={startDate}
                    className="px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </>
              )}
            </div>
            
            <button
              onClick={fetchPatients}
              disabled={patientsLoading}
              className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm flex items-center gap-2 transition-all disabled:opacity-50"
            >
              {patientsLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              조회
            </button>
          </div>
          
          {/* 기간 정보 표시 */}
          {dateRangeMode && startDate && endDate && (
            <div className="text-sm text-slate-400">
              {startDate === endDate 
                ? `${startDate}` 
                : `${startDate} ~ ${endDate}`}
            </div>
          )}
        </div>
        
        {/* 빠른 날짜 선택 버튼 */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-500">빠른 선택:</span>
          {[
            { label: '오늘', days: 0 },
            { label: '어제', days: -1 },
            { label: '최근 3일', days: -2, range: true },
            { label: '최근 7일', days: -6, range: true },
            { label: '최근 30일', days: -29, range: true },
          ].map(({ label, days, range }) => {
            const today = new Date()
            const targetDate = new Date()
            targetDate.setDate(today.getDate() + days)
            const targetDateStr = targetDate.toISOString().split('T')[0]
            const todayStr = today.toISOString().split('T')[0]
            
            return (
              <button
                key={label}
                onClick={() => {
                  if (range) {
                    setDateRangeMode(true)
                    setStartDate(targetDateStr)
                    setEndDate(todayStr)
                  } else {
                    setDateRangeMode(false)
                    setStartDate(targetDateStr)
                    setEndDate(targetDateStr)
                  }
                }}
                className="px-2 py-1 rounded text-xs bg-slate-800/60 hover:bg-slate-700/80 text-slate-400 hover:text-white transition-all"
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 환자 리스트 */}
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-rose-400" />
              XA 환자 리스트
              {patients.length > 0 && (
                <span className="text-sm text-slate-400">({patients.length}명)</span>
              )}
            </h2>
            
            {patients.length > 0 && (
              <button
                onClick={toggleAllPatients}
                className="text-sm text-slate-400 hover:text-white transition-all"
              >
                {selectedPatients.length === patients.length ? '전체 해제' : '전체 선택'}
              </button>
            )}
          </div>
          
          {patientsError && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 mb-4">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                <p className="text-red-300 text-sm">{patientsError}</p>
              </div>
            </div>
          )}
          
          <div className="space-y-2 max-h-[400px] overflow-auto">
            {patientsLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-rose-400 animate-spin mb-4" />
                <p className="text-slate-400">환자 리스트 조회 중...</p>
              </div>
            ) : patients.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Search className="w-12 h-12 text-slate-600 mb-4" />
                <p className="text-slate-400 mb-2">환자가 없습니다</p>
                <p className="text-sm text-slate-500">날짜를 변경하거나 새로고침해보세요</p>
              </div>
            ) : (
              patients.map((patient) => {
                const isSelected = selectedPatients.some(p => p.cine_no === patient.cine_no)
                return (
                  <div
                    key={patient.cine_no}
                    className={`p-4 rounded-xl transition-all duration-200 ${
                      isSelected
                        ? 'bg-rose-500/20 border border-rose-500/50'
                        : 'bg-slate-800/50 border border-transparent hover:bg-slate-700/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div 
                        onClick={() => togglePatient(patient)}
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-rose-500 border-rose-500'
                            : 'border-slate-500 hover:border-rose-400'
                        }`}
                      >
                        {isSelected && <CheckCircle className="w-4 h-4 text-white" />}
                      </div>
                      <div className="flex-1 cursor-pointer" onClick={() => togglePatient(patient)}>
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-slate-400" />
                          <span className="font-medium text-white">{patient.patient_name || '이름없음'}</span>
                          <span className="text-sm text-slate-400">
                            ({patient.gender || '-'}/{patient.age || '-'})
                          </span>
                          {/* 기간 선택 모드에서 검사 날짜 표시 */}
                          {dateRangeMode && patient.study_date && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300">
                              {patient.study_date.split(' ').pop()}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-500 mt-1">
                          ID: {patient.patient_id} | 검사번호: {patient.cine_no}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          fetchPreview(patient)
                        }}
                        className="px-3 py-1.5 text-xs rounded-lg bg-violet-600/30 hover:bg-violet-600/50 text-violet-300 hover:text-white transition-all flex items-center gap-1"
                      >
                        <Image className="w-3.5 h-3.5" />
                        미리보기
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
          
          {selectedPatients.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-700">
              <button
                onClick={startOCR}
                disabled={ocrLoading}
                className="w-full py-4 px-6 rounded-xl bg-gradient-to-r from-rose-600 to-pink-600 hover:from-rose-500 hover:to-pink-500 text-white font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 glow-pink"
              >
                {ocrLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    OCR 처리 중... ({jobStatus?.completed || 0}/{jobStatus?.total || selectedPatients.length})
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    선택된 {selectedPatients.length}명 OCR 시작
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* OCR 결과 */}
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Heart className="w-5 h-5 text-rose-400" />
              OCR 결과
              {ocrResults.length > 0 && (
                <span className="text-sm text-slate-400">
                  ({ocrResults.filter(r => r.success).length}/{ocrResults.length} 성공)
                </span>
              )}
            </h2>
            
            {ocrResults.length > 0 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowExtractionModal(true)}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 hover:text-white text-sm flex items-center gap-2 transition-all"
                  title="데이터 추출"
                >
                  <FileSpreadsheet className="w-4 h-4" />
                  데이터 추출
                </button>
                <button
                  onClick={downloadAllResults}
                  className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                  title="전체 다운로드"
                >
                  <Download className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>
          
          {/* 진행 상태 */}
          {ocrLoading && jobStatus && (
            <div className="mb-4 p-4 rounded-xl bg-slate-800/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-400">진행률</span>
                <span className="text-sm text-white">
                  {jobStatus.completed}/{jobStatus.total}
                </span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-rose-500 to-pink-500 transition-all duration-300"
                  style={{ width: `${(jobStatus.completed / jobStatus.total) * 100}%` }}
                />
              </div>
              {jobStatus.current && (
                <p className="text-xs text-slate-500 mt-2">처리 중: {jobStatus.current}</p>
              )}
            </div>
          )}
          
          {/* 결과 리스트 */}
          <div className="space-y-2 max-h-[300px] overflow-auto">
            {ocrResults.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <BarChart3 className="w-12 h-12 text-slate-600 mb-4" />
                <p className="text-slate-400 mb-2">아직 결과가 없습니다</p>
                <p className="text-sm text-slate-500">환자를 선택하고 OCR을 시작하세요</p>
              </div>
            ) : (
              ocrResults.map((result, index) => (
                <div
                  key={index}
                  onClick={() => setSelectedResult(result)}
                  className={`p-3 rounded-xl cursor-pointer transition-all ${
                    selectedResult === result
                      ? 'bg-rose-500/20 border border-rose-500/50'
                      : 'bg-slate-800/50 hover:bg-slate-700/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {result.success ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-400" />
                      )}
                      <span className="font-medium text-white">
                        [{result.patient_id}] {result.patient_name}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500">
                      {result.processing_time?.toFixed(1)}초
                    </span>
                  </div>
                  {result.success && result.lines && (
                    <p className="text-xs text-slate-400 mt-1 truncate">
                      {result.lines.length}줄 인식됨
                    </p>
                  )}
                  {!result.success && (
                    <p className="text-xs text-red-400 mt-1 truncate">{result.error}</p>
                  )}
                </div>
              ))
            )}
          </div>
          
          {/* 선택된 결과 상세 */}
          {selectedResult && selectedResult.success && (
            <div className="mt-4 pt-4 border-t border-slate-700">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-white">
                  [{selectedResult.patient_id}] {selectedResult.patient_name}
                </h3>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(selectedResult.text)
                  }}
                  className="p-1 rounded text-slate-400 hover:text-white transition-all"
                  title="복사"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-700/50 max-h-[200px] overflow-auto">
                <pre className="whitespace-pre-wrap text-xs text-slate-300 font-mono">
                  {selectedResult.text || '(인식된 텍스트 없음)'}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 미리보기 모달 */}
      {previewPatient && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 max-w-4xl w-full max-h-[90vh] overflow-hidden">
            {/* 모달 헤더 */}
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <div className="flex items-center gap-3">
                <Image className="w-5 h-5 text-violet-400" />
                <div>
                  <h3 className="font-semibold text-white">
                    [{previewPatient.patient_id}] {previewPatient.patient_name || '이름없음'}
                  </h3>
                  <p className="text-xs text-slate-400">검사번호: {previewPatient.cine_no}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {previewTotal > 0 && (
                  <span className="text-sm text-slate-400 bg-slate-800 px-3 py-1 rounded-lg">
                    {previewIndex + 1} / {previewTotal}
                  </span>
                )}
                <button
                  onClick={closePreview}
                  className="p-2 rounded-lg hover:bg-slate-700/50 text-slate-400 hover:text-white transition-all"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* 모달 본문 */}
            <div className="p-4 max-h-[calc(90vh-140px)] overflow-auto">
              {previewLoading ? (
                <div className="flex flex-col items-center justify-center py-20">
                  <Loader2 className="w-10 h-10 text-violet-400 animate-spin mb-4" />
                  <p className="text-slate-400">리포트 이미지 로딩 중...</p>
                </div>
              ) : previewError ? (
                <div className="flex flex-col items-center justify-center py-20">
                  <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
                  <p className="text-red-400 mb-2">미리보기 실패</p>
                  <p className="text-sm text-slate-500">{previewError}</p>
                </div>
              ) : previewImage ? (
                <div className="flex flex-col items-center gap-3">
                  <img 
                    src={previewImage} 
                    alt="리포트 미리보기" 
                    className="max-w-full h-auto rounded-xl border border-slate-700"
                  />
                  {previewCurrentUrl && (
                    <div className="w-full p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-violet-400">📍 요청 URL</span>
                        {previewCurrentUrl.includes('.dcm/W0001.jpg') ? (
                          <span className="text-xs text-green-400">✅ 올바른 형식</span>
                        ) : (
                          <span className="text-xs text-red-400">❌ 잘못된 형식</span>
                        )}
                        <button
                          onClick={() => navigator.clipboard.writeText(previewCurrentUrl)}
                          className="text-xs text-slate-400 hover:text-white transition-all ml-auto"
                          title="URL 복사"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      </div>
                      <p className="text-xs text-slate-300 font-mono break-all">{previewCurrentUrl}</p>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
            
            {/* 이미지 네비게이션 */}
            {previewTotal > 1 && !previewLoading && (
              <div className="flex items-center justify-center gap-4 p-4 border-t border-slate-700">
                <button
                  onClick={prevImage}
                  disabled={previewIndex <= 0}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                >
                  <ChevronRight className="w-4 h-4 rotate-180" />
                  이전
                </button>
                <span className="text-slate-400">
                  이미지 {previewIndex + 1} / {previewTotal}
                </span>
                <button
                  onClick={nextImage}
                  disabled={previewIndex >= previewTotal - 1}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                >
                  다음
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 데이터 추출 모달 */}
      <ExtractionModal
        isOpen={showExtractionModal}
        onClose={() => setShowExtractionModal(false)}
        ocrResults={ocrResults.filter(r => r.success)}
        startDate={startDate}
        endDate={endDate}
        dateRangeMode={dateRangeMode}
        patients={patients}
      />
    </div>
  )
}

// 메인 App 컴포넌트
function App() {
  const [activeTab, setActiveTab] = useState('file')
  const [showSettings, setShowSettings] = useState(false)
  
  // Settings
  const [language, setLanguage] = useState('korean')
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.3)
  const [showConfidence, setShowConfidence] = useState(false)

  return (
    <div className="min-h-screen p-6 md:p-8">
      {/* Header */}
      <header className="max-w-6xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 glow-purple">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-violet-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                PaddleOCR
              </h1>
              <p className="text-sm text-slate-400">이미지 텍스트 추출기</p>
            </div>
          </div>
          
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-3 rounded-xl transition-all duration-300 ${
              showSettings 
                ? 'bg-violet-500/20 text-violet-400 glow-purple' 
                : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
            }`}
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto">
        {/* Tab Navigation */}
        <div className="flex items-center gap-3 mb-6">
          <TabButton
            active={activeTab === 'file'}
            onClick={() => setActiveTab('file')}
            icon={Upload}
          >
            파일 OCR
          </TabButton>
          <TabButton
            active={activeTab === 'dcas'}
            onClick={() => setActiveTab('dcas')}
            icon={Hospital}
          >
            Dcas OCR
          </TabButton>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="glass rounded-2xl p-6 mb-6 animate-fade-in">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5 text-violet-400" />
              설정
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Language */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  인식 언어
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl bg-slate-800/80 border border-slate-700 text-white focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
                >
                  {languages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Confidence Threshold */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  신뢰도 임계값: {Math.round(confidenceThreshold * 100)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-violet-500"
                />
              </div>

              {/* Show Confidence */}
              <div className="flex items-center">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showConfidence}
                    onChange={(e) => setShowConfidence(e.target.checked)}
                    className="w-5 h-5 rounded bg-slate-800 border-slate-600 text-violet-500 focus:ring-violet-500 focus:ring-offset-0"
                  />
                  <span className="text-sm text-slate-300">결과에 신뢰도 표시</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'file' ? (
          <FileOCRTab
            language={language}
            confidenceThreshold={confidenceThreshold}
            showConfidence={showConfidence}
          />
        ) : (
          <DcasOCRTab
            language={language}
            confidenceThreshold={confidenceThreshold}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto mt-12 text-center text-sm text-slate-500">
        <p>Powered by PaddleOCR • Built with React + Tailwind CSS</p>
      </footer>
    </div>
  )
}

export default App
