'use client'

import Image from "next/image"
import { useState, useRef, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { ArrowUp, Loader2, CheckCircle, XCircle, Key, Database, Brain, Save, TestTube, Eye, EyeOff } from "lucide-react"
import { cn } from "@/lib/utils"
import RevealOnView from "@/components/reveal-on-view"
import { useSingleUrlProcessing, useBatchProcessing, useHistory, useSettings, ProcessingStatus } from "@/lib/store"
import { isValidUrl, parseBatchUrls, formatTimestamp, formatProcessingTime } from "@/lib/utils"

type Props = {
  title?: string
  subtitle?: string
  imageSrc?: string
  tags?: string[]
  href?: string
  priority?: boolean
  gradientFrom?: string
  gradientTo?: string
  imageContainerClassName?: string
  containerClassName?: string
  revealDelay?: number
}

// Client Component (now handles user interactions)
export default function ProjectCard({
  title = "Project title",
  subtitle = "Project subtitle",
  imageSrc = "/placeholder.svg?height=720&width=1280",
  tags = ["Design", "Web"],
  href = "#",
  priority = false,
  gradientFrom = "#0f172a",
  gradientTo = "#6d28d9",
  imageContainerClassName,
  containerClassName,
  revealDelay = 0,
}: Props) {
  const [url, setUrl] = useState("")
  const [batchUrls, setBatchUrls] = useState("")
  const [settingsForm, setSettingsForm] = useState({
    qwen_api_key: "",
    notion_api_key: "",
    notion_database_id: ""
  })
  const [testResults, setTestResults] = useState<Record<string, boolean>>({})
  const [isTesting, setIsTesting] = useState(false)
  const [showPasswords, setShowPasswords] = useState({
    qwen_api_key: false,
    notion_api_key: false
  })
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // 使用状态管理 hooks
  const singleUrl = useSingleUrlProcessing()
  const batch = useBatchProcessing()
  const history = useHistory()
  const settings = useSettings()

  // Auto-resize textarea
  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }

  useEffect(() => {
    adjustTextareaHeight()
  }, [batchUrls])

  // 加载设置数据
  useEffect(() => {
    if (title === "设置") {
      settings.load()
    }
  }, [title, settings.load])

  // 当设置数据更新时同步到表单
  useEffect(() => {
    if (settings.data) {
      setSettingsForm({
        qwen_api_key: settings.data.qwen_api_key || "",
        notion_api_key: settings.data.notion_api_key || "",
        notion_database_id: settings.data.notion_database_id || ""
      })
    }
  }, [settings.data])

  const handleSubmit = async () => {
    if (!url.trim()) return
    
    if (!isValidUrl(url.trim())) {
      alert('请输入有效的URL地址')
      return
    }
    
    try {
      await singleUrl.process(url.trim())
    } catch (error) {
      console.error('URL处理失败:', error)
    }
  }

  const handleBatchSubmit = async () => {
    if (!batchUrls.trim()) return
    
    const urlList = parseBatchUrls(batchUrls)
    if (urlList.length === 0) {
      alert('请输入至少一个有效的URL地址')
      return
    }
    
    try {
      await batch.process(urlList)
    } catch (error) {
      console.error('批量处理失败:', error)
    }
  }

  const handleBatchUrlsChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setBatchUrls(e.target.value)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit()
    }
  }

  // 设置表单处理函数
  const handleSettingsChange = (field: string, value: string) => {
    setSettingsForm(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSaveSettings = async () => {
    try {
      // 只保存非空的字段
      const updates: any = {}
      if (settingsForm.qwen_api_key.trim()) {
        updates.qwen_api_key = settingsForm.qwen_api_key.trim()
      }
      if (settingsForm.notion_api_key.trim()) {
        updates.notion_api_key = settingsForm.notion_api_key.trim()
      }
      if (settingsForm.notion_database_id.trim()) {
        updates.notion_database_id = settingsForm.notion_database_id.trim()
      }

      await settings.save(updates)
      console.log('设置保存成功')
    } catch (error) {
      console.error('设置保存失败:', error)
    }
  }

  const handleTestSettings = async () => {
    setIsTesting(true)
    setTestResults({})
    
    try {
      // 准备测试数据
      const testData: any = {}
      if (settingsForm.qwen_api_key.trim()) {
        testData.qwen_api_key = settingsForm.qwen_api_key.trim()
      }
      if (settingsForm.notion_api_key.trim()) {
        testData.notion_api_key = settingsForm.notion_api_key.trim()
      }
      if (settingsForm.notion_database_id.trim()) {
        testData.notion_database_id = settingsForm.notion_database_id.trim()
      }

      const success = await settings.test(testData)
      
      // 这里应该从API响应中获取详细的测试结果，暂时简化处理
      setTestResults({
        qwen_api_key: !!testData.qwen_api_key && success,
        notion_api_key: !!testData.notion_api_key && success,
        notion_database_id: !!testData.notion_database_id && success
      })
    } catch (error) {
      console.error('设置测试失败:', error)
      setTestResults({
        qwen_api_key: false,
        notion_api_key: false,
        notion_database_id: false
      })
    } finally {
      setIsTesting(false)
    }
  }

  const togglePasswordVisibility = (field: 'qwen_api_key' | 'notion_api_key') => {
    setShowPasswords(prev => ({
      ...prev,
      [field]: !prev[field]
    }))
  }
  return (
    <article className={cn("group relative", containerClassName)}>
      <RevealOnView
        delay={revealDelay}
        className="rounded-3xl border border-white/10 p-1 shadow-[0_10px_60px_-10px_rgba(0,0,0,0.6)] lg:h-full"
        style={{
          backgroundImage: `linear-gradient(135deg, ${gradientFrom}, ${gradientTo})`,
        }}
      >
        <div className="relative overflow-hidden rounded-[1.35rem] bg-black lg:h-full">
          {/* Image */}
          <div className={cn("relative w-full aspect-[4/3] sm:aspect-[16/9] lg:aspect-auto lg:h-full", imageContainerClassName)}>
            <Image
              src={imageSrc || "/placeholder.svg"}
              alt={title}
              fill
              sizes="(min-width: 1024px) 66vw, 100vw"
              priority={priority}
              className="object-cover"
            />
            {/* Subtle vignette */}
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-black/30" />
          </div>

          {/* Top-left title and tags */}
          <div className="absolute left-4 top-4 space-y-2">
            <div>
              <h3 className="text-lg font-semibold sm:text-xl">{title}</h3>
              <p className="text-sm text-white/70">{subtitle}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {tags.map((t) => (
                <Badge
                  key={t}
                  variant="secondary"
                  className="pointer-events-auto bg-black/50 text-white border-white/20 backdrop-blur-sm"
                >
                  {t}
                </Badge>
              ))}
            </div>
          </div>

          {/* Center content for inputs */}
          <div className="absolute inset-0 flex items-center justify-center p-4">
            {/* Special content for single URL card */}
            {title === "单个URL解析" && (
              <div className="w-[60%] space-y-3">
                {/* URL Input */}
                <div className="flex items-center gap-2">
                  <Input 
                    placeholder="请输入URL地址..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={singleUrl.isLoading}
                    className="bg-white/10 border-white/20 text-white placeholder:text-white/50 backdrop-blur-sm flex-1 focus:bg-white/20 transition-colors disabled:opacity-50"
                  />
                  <Button 
                    size="sm" 
                    onClick={handleSubmit}
                    disabled={singleUrl.isLoading || !url.trim()}
                    className="bg-white text-black hover:bg-white/90 rounded-full w-10 h-10 p-0 shrink-0 disabled:opacity-50"
                  >
                    {singleUrl.isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ArrowUp className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                
                {/* Status Display */}
                {singleUrl.status !== ProcessingStatus.IDLE && (
                  <div className="flex items-center justify-center gap-2 text-xs">
                    {singleUrl.status === ProcessingStatus.PROCESSING && (
                      <>
                        <Loader2 className="h-3 w-3 animate-spin" />
                        <span className="text-white/70">正在处理中...</span>
                      </>
                    )}
                    {singleUrl.status === ProcessingStatus.SUCCESS && (
                      <>
                        <CheckCircle className="h-3 w-3 text-green-400" />
                        <span className="text-green-400">处理成功</span>
                      </>
                    )}
                    {singleUrl.status === ProcessingStatus.ERROR && (
                      <>
                        <XCircle className="h-3 w-3 text-red-400" />
                        <span className="text-red-400">处理失败</span>
                      </>
                    )}
                  </div>
                )}
                
                {/* Description */}
                <p className="text-xs text-white/60 leading-relaxed text-center">
                  输入URL地址，系统将自动解析数据并添加到数据库中。
                </p>
              </div>
            )}

            {/* Special content for batch processing card */}
            {title === "批量处理" && (
              <div className="w-[60%] space-y-3">
                <div className="relative">
                  <Textarea 
                    ref={textareaRef}
                    placeholder="请输入多个URL，每行一个..."
                    value={batchUrls}
                    onChange={handleBatchUrlsChange}
                    disabled={batch.status === ProcessingStatus.PROCESSING}
                    className="bg-white/10 border-white/20 text-white placeholder:text-white/50 backdrop-blur-sm focus:bg-white/20 transition-colors resize-none min-h-[100px] overflow-hidden disabled:opacity-50"
                    rows={4}
                  />
                  <Button 
                    size="sm" 
                    onClick={handleBatchSubmit}
                    disabled={batch.status === ProcessingStatus.PROCESSING || !batchUrls.trim()}
                    className="absolute bottom-2 right-2 bg-white text-black hover:bg-white/90 rounded-full w-8 h-8 p-0 disabled:opacity-50"
                  >
                    {batch.status === ProcessingStatus.PROCESSING ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <ArrowUp className="h-3 w-3" />
                    )}
                  </Button>
                </div>
                
                {/* Batch Status Display */}
                {batch.status !== ProcessingStatus.IDLE && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-center gap-2 text-xs">
                      {batch.status === ProcessingStatus.PROCESSING && (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          <span className="text-white/70">
                            批量处理中... ({batch.processedCount}/{batch.totalCount})
                          </span>
                        </>
                      )}
                      {batch.status === ProcessingStatus.SUCCESS && (
                        <>
                          <CheckCircle className="h-3 w-3 text-green-400" />
                          <span className="text-green-400">
                            批量处理完成: {batch.successCount} 成功, {batch.failureCount} 失败
                          </span>
                        </>
                      )}
                      {batch.status === ProcessingStatus.ERROR && (
                        <>
                          <XCircle className="h-3 w-3 text-red-400" />
                          <span className="text-red-400">批量处理失败</span>
                        </>
                      )}
                    </div>
                    
                    {/* Progress Bar */}
                    {batch.status === ProcessingStatus.PROCESSING && batch.totalCount > 0 && (
                      <div className="w-full bg-white/20 rounded-full h-1">
                        <div 
                          className="bg-white/70 h-1 rounded-full transition-all duration-300"
                          style={{ width: `${(batch.processedCount / batch.totalCount) * 100}%` }}
                        />
                      </div>
                    )}
                  </div>
                )}
                
                {/* Description */}
                <p className="text-xs text-white/60 leading-relaxed text-center">
                  输入多个URL进行批量处理，系统会自动解析所有URL并将数据添加到数据库中。
                </p>
              </div>
            )}

            {/* Special content for results card */}
            {title === "处理结果" && (
              <div className="w-[90%] h-[80%] space-y-3">
                                  {/* Header */}
                  <div className="flex items-center justify-end mb-4">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-white/60">共 {history.history.length} 条</span>
                      {history.history.length > 0 && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={history.clear}
                          className="h-6 px-2 text-xs text-white/60 hover:text-white/80 hover:bg-white/10"
                        >
                          清空
                        </Button>
                      )}
                    </div>
                  </div>

                {/* History List */}
                <div className="h-full overflow-hidden">
                  {history.history.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-white/50">
                      <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center mb-3">
                        <CheckCircle className="h-6 w-6" />
                      </div>
                      <p className="text-sm">暂无处理记录</p>
                      <p className="text-xs mt-1">开始处理URL后，记录将显示在这里</p>
                    </div>
                  ) : (
                    <div className="h-full overflow-y-auto space-y-2 pr-2 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
                      {history.history.slice(0, 20).map((record) => (
                        <div
                          key={record.id}
                          className={cn(
                            "p-3 rounded-lg backdrop-blur-md border",
                            "bg-white/5 border-white/10",
                            "hover:bg-white/10 transition-all duration-200",
                            record.success 
                              ? "hover:border-green-400/30" 
                              : "hover:border-red-400/30"
                          )}
                        >
                          {/* Record Header */}
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              {record.success ? (
                                <CheckCircle className="h-3 w-3 text-green-400 shrink-0" />
                              ) : (
                                <XCircle className="h-3 w-3 text-red-400 shrink-0" />
                              )}
                              <span className="text-xs text-white/90 truncate">
                                {new URL(record.url).hostname}
                              </span>
                            </div>
                            <span className="text-xs text-white/50 shrink-0">
                              {formatTimestamp(record.timestamp)}
                            </span>
                          </div>

                          {/* Record Details */}
                          <div className="space-y-1">
                            <div className="text-xs text-white/70 truncate">
                              {record.url}
                            </div>
                            
                            {record.success ? (
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-green-400/80">
                                  ✓ 处理成功
                                </span>
                                {record.processingTime && (
                                  <span className="text-white/50">
                                    {formatProcessingTime(record.processingTime / 1000)}
                                  </span>
                                )}
                              </div>
                            ) : (
                              <div className="text-xs text-red-400/80">
                                ✗ {record.errorMessage || '处理失败'}
                              </div>
                            )}

                            {/* Notion Link */}
                            {record.success && record.notionPageUrl && (
                              <a
                                href={record.notionPageUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-blue-400/80 hover:text-blue-400 transition-colors mt-1"
                              >
                                <span>→ 查看Notion页面</span>
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                      
                      {history.history.length > 20 && (
                        <div className="text-center py-2">
                          <span className="text-xs text-white/50">
                            仅显示最近20条记录
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Export Button */}
                {history.history.length > 0 && (
                  <div className="flex justify-center pt-2 border-t border-white/10">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={history.export}
                      className="text-xs bg-white/5 border-white/20 text-white/80 hover:bg-white/10 hover:text-white"
                    >
                      导出记录
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Special content for settings card */}
            {title === "设置" && (
              <div className="w-[85%] h-[85%] space-y-4 overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
                {/* Header */}
                <div className="text-center space-y-2 mb-4">
                  <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center mx-auto">
                    <svg className="h-4 w-4 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.350 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.350a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.350 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.350a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <p className="text-sm text-white/90 font-medium">API配置</p>
                </div>

                {/* Qwen API Key */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Brain className="h-4 w-4 text-white/60" />
                    <label className="text-xs text-white/70 font-medium">Qwen LLM API Key</label>
                    {testResults.qwen_api_key === true && <CheckCircle className="h-3 w-3 text-green-400" />}
                    {testResults.qwen_api_key === false && <XCircle className="h-3 w-3 text-red-400" />}
                  </div>
                  <div className="relative">
                    <Input
                      type={showPasswords.qwen_api_key ? "text" : "password"}
                      placeholder="留空则使用环境变量..."
                      value={settingsForm.qwen_api_key}
                      onChange={(e) => handleSettingsChange('qwen_api_key', e.target.value)}
                      disabled={settings.isLoading}
                      className="bg-white/5 border-white/20 text-white text-xs placeholder:text-white/40 pr-8 focus:bg-white/10"
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => togglePasswordVisibility('qwen_api_key')}
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0 hover:bg-white/10"
                    >
                      {showPasswords.qwen_api_key ? (
                        <EyeOff className="h-3 w-3 text-white/60" />
                      ) : (
                        <Eye className="h-3 w-3 text-white/60" />
                      )}
                    </Button>
                  </div>
                </div>

                {/* Notion API Key */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Key className="h-4 w-4 text-white/60" />
                    <label className="text-xs text-white/70 font-medium">Notion API Key</label>
                    {testResults.notion_api_key === true && <CheckCircle className="h-3 w-3 text-green-400" />}
                    {testResults.notion_api_key === false && <XCircle className="h-3 w-3 text-red-400" />}
                  </div>
                  <div className="relative">
                    <Input
                      type={showPasswords.notion_api_key ? "text" : "password"}
                      placeholder="留空则使用环境变量..."
                      value={settingsForm.notion_api_key}
                      onChange={(e) => handleSettingsChange('notion_api_key', e.target.value)}
                      disabled={settings.isLoading}
                      className="bg-white/5 border-white/20 text-white text-xs placeholder:text-white/40 pr-8 focus:bg-white/10"
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => togglePasswordVisibility('notion_api_key')}
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0 hover:bg-white/10"
                    >
                      {showPasswords.notion_api_key ? (
                        <EyeOff className="h-3 w-3 text-white/60" />
                      ) : (
                        <Eye className="h-3 w-3 text-white/60" />
                      )}
                    </Button>
                  </div>
                </div>

                {/* Notion Database ID */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-white/60" />
                    <label className="text-xs text-white/70 font-medium">Notion Database ID</label>
                    {testResults.notion_database_id === true && <CheckCircle className="h-3 w-3 text-green-400" />}
                    {testResults.notion_database_id === false && <XCircle className="h-3 w-3 text-red-400" />}
                  </div>
                  <Input
                    type="text"
                    placeholder="留空则使用环境变量..."
                    value={settingsForm.notion_database_id}
                    onChange={(e) => handleSettingsChange('notion_database_id', e.target.value)}
                    disabled={settings.isLoading}
                    className="bg-white/5 border-white/20 text-white text-xs placeholder:text-white/40 focus:bg-white/10"
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-2">
                  <Button
                    size="sm"
                    onClick={handleTestSettings}
                    disabled={isTesting || settings.isLoading}
                    className="flex-1 bg-blue-500/20 border border-blue-400/30 text-blue-300 hover:bg-blue-500/30 text-xs"
                  >
                    {isTesting ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <TestTube className="h-3 w-3 mr-1" />
                    )}
                    测试
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSaveSettings}
                    disabled={settings.isLoading}
                    className="flex-1 bg-green-500/20 border border-green-400/30 text-green-300 hover:bg-green-500/30 text-xs"
                  >
                    {settings.isLoading ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <Save className="h-3 w-3 mr-1" />
                    )}
                    保存
                  </Button>
                </div>

                {/* Status Message */}
                {settings.lastSaved && (
                  <div className="text-center">
                    <p className="text-xs text-green-400/80">
                      ✓ 设置已保存 {new Date(settings.lastSaved).toLocaleTimeString()}
                    </p>
                  </div>
                )}

                {/* Help Text */}
                <div className="text-center pt-2 border-t border-white/10">
                  <p className="text-xs text-white/50 leading-relaxed">
                    留空字段将使用.env文件中的环境变量作为默认值
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </RevealOnView>
    </article>
  )
}
