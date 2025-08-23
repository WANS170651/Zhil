/**
 * URL信息收集和存储系统 - Web界面JavaScript
 * 处理所有前端交互逻辑和API调用
 */

// 全局配置
const CONFIG = {
    API_BASE_URL: window.location.origin, // 自动使用当前页面的主机和端口
    POLL_INTERVAL: 1000,
    MAX_RETRIES: 3,
    TIMEOUT: 30000
};

// 全局状态
const STATE = {
    isProcessing: false,
    processingHistory: JSON.parse(localStorage.getItem('processingHistory') || '[]'),
    systemStatus: null,
    batchProgress: {
        current: 0,
        total: 0,
        results: []
    }
};

// DOM元素缓存
const ELEMENTS = {};

/**
 * 页面初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 URL信息收集系统Web界面初始化中...');
    
    // 缓存DOM元素
    cacheElements();
    
    // 绑定事件监听器
    bindEventListeners();
    
    // 初始化系统状态
    initializeSystem();
    
    // 加载历史记录
    loadProcessingHistory();
    
    console.log('✅ Web界面初始化完成');
});

/**
 * 缓存常用DOM元素
 */
function cacheElements() {
    ELEMENTS.statusText = document.getElementById('status-text');
    ELEMENTS.systemStatus = document.getElementById('system-status');
    ELEMENTS.alertContainer = document.getElementById('alert-container');
    
    // 单URL处理相关
    ELEMENTS.singleUrlForm = document.getElementById('single-url-form');
    ELEMENTS.singleUrlInput = document.getElementById('single-url-input');
    ELEMENTS.singleUrlSubmit = document.getElementById('single-url-submit');
    ELEMENTS.singleUrlStatus = document.getElementById('single-url-status');
    ELEMENTS.singleUrlStage = document.getElementById('single-url-stage');
    ELEMENTS.singleUrlProgress = document.getElementById('single-url-progress');
    ELEMENTS.singleUrlResult = document.getElementById('single-url-result');
    
    // 批量处理相关
    ELEMENTS.batchUrlsForm = document.getElementById('batch-urls-form');
    ELEMENTS.batchUrlsInput = document.getElementById('batch-urls-input');
    ELEMENTS.batchUrlsSubmit = document.getElementById('batch-urls-submit');
    ELEMENTS.batchUrlCount = document.getElementById('batch-url-count');
    ELEMENTS.batchProcessingStatus = document.getElementById('batch-processing-status');
    ELEMENTS.batchCurrentStatus = document.getElementById('batch-current-status');
    ELEMENTS.batchProgress = document.getElementById('batch-progress');
    ELEMENTS.batchProcessed = document.getElementById('batch-processed');
    ELEMENTS.batchTotal = document.getElementById('batch-total');
    ELEMENTS.batchResults = document.getElementById('batch-results');
    
    // 结果和设置相关
    ELEMENTS.resultsContainer = document.getElementById('results-container');
    ELEMENTS.healthStatus = document.getElementById('health-status');
    
    // 设置相关
    ELEMENTS.apiSettingsForm = document.getElementById('api-settings-form');
    ELEMENTS.qwenApiKey = document.getElementById('qwen-api-key');
    ELEMENTS.notionApiKey = document.getElementById('notion-api-key');
    ELEMENTS.notionDatabaseId = document.getElementById('notion-database-id');
}

/**
 * 绑定事件监听器
 */
function bindEventListeners() {
    // 单URL处理表单
    if (ELEMENTS.singleUrlForm) {
        ELEMENTS.singleUrlForm.addEventListener('submit', handleSingleUrlSubmit);
    }
    
    // 批量URL处理表单
    if (ELEMENTS.batchUrlsForm) {
        ELEMENTS.batchUrlsForm.addEventListener('submit', handleBatchUrlsSubmit);
    }
    
    // URL数量统计
    if (ELEMENTS.batchUrlsInput) {
        ELEMENTS.batchUrlsInput.addEventListener('input', updateBatchUrlCount);
    }
    
    // 设置表单
    if (ELEMENTS.apiSettingsForm) {
        ELEMENTS.apiSettingsForm.addEventListener('submit', handleSettingsSubmit);
    }
    
    // 示例URL按钮
    document.querySelectorAll('.example-url').forEach(btn => {
        btn.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            if (ELEMENTS.singleUrlInput) {
                ELEMENTS.singleUrlInput.value = url;
                // 可选：自动切换到单URL标签页
                const singleUrlTab = document.getElementById('single-url-tab');
                if (singleUrlTab) {
                    singleUrlTab.click();
                }
            }
        });
    });
    
    // 标签页切换事件
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            const targetId = e.target.getAttribute('data-bs-target').substring(1);
            handleTabSwitch(targetId);
        });
    });
}

/**
 * 系统初始化
 */
async function initializeSystem() {
    console.log('🔍 检查系统状态...');
    console.log('🔧 当前配置:', CONFIG);
    console.log('🌐 当前页面信息:', {
        origin: window.location.origin,
        href: window.location.href,
        protocol: window.location.protocol,
        host: window.location.host
    });
    
    updateSystemStatus('检查中...', 'warning');
    
    try {
        // 检查API连接
        console.log('📡 开始API健康检查...');
        const response = await fetchAPI('/health');
        console.log('📡 API健康检查响应:', response);
        
        if (response.status === 'healthy') {
            updateSystemStatus('系统正常', 'success');
            STATE.systemStatus = 'healthy';
            console.log('✅ 系统状态检查成功');
        } else {
            updateSystemStatus('系统异常', 'danger');
            STATE.systemStatus = 'unhealthy';
            console.log('⚠️ 系统状态异常:', response);
        }
        
        // 加载设置
        console.log('⚙️ 开始加载设置...');
        await loadSettings();
        console.log('✅ 设置加载完成');
        
    } catch (error) {
        console.error('❌ 系统状态检查失败:', error);
        console.error('❌ 错误堆栈:', error.stack);
        updateSystemStatus('连接失败', 'danger');
        STATE.systemStatus = 'error';
        
        showAlert('warning', '系统连接失败', '无法连接到后端API服务，请确保服务正在运行。');
    }
}

/**
 * 更新系统状态显示
 */
function updateSystemStatus(text, type) {
    if (ELEMENTS.statusText) {
        ELEMENTS.statusText.textContent = text;
    }
    
    if (ELEMENTS.systemStatus) {
        const icon = ELEMENTS.systemStatus.querySelector('i');
        if (icon) {
            icon.className = `bi bi-circle-fill text-${type}`;
        }
    }
}

/**
 * 处理单URL提交
 */
async function handleSingleUrlSubmit(event) {
    event.preventDefault();
    
    const url = ELEMENTS.singleUrlInput.value.trim();
    if (!url) {
        showAlert('warning', '请输入URL', '请输入一个有效的URL地址。');
        return;
    }
    
    if (!isValidUrl(url)) {
        showAlert('danger', 'URL格式错误', '请输入一个有效的HTTP/HTTPS URL。');
        return;
    }
    
    await processSingleUrl(url);
}

/**
 * 处理单个URL
 */
async function processSingleUrl(url) {
    console.log(`🚀 开始处理URL: ${url}`);
    
    // 显示处理状态
    showProcessingStatus(true);
    setProcessingState(true);
    
    const startTime = Date.now();
    let result = null;
    
    try {
        // 调用API处理URL
        updateProcessingStage('开始处理...');
        updateProcessingProgress(10);
        
        const response = await fetchAPI('/ingest/url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });
        
        updateProcessingProgress(100);
        
        // 处理响应
        if (response.success) {
            result = {
                url: url,
                success: true,
                data: response,
                timestamp: new Date().toISOString(),
                processingTime: Date.now() - startTime
            };
            
            showProcessingResult(result);
            showAlert('success', '处理成功', `URL "${url}" 已成功处理并存储到Notion数据库。`);
            
        } else {
            throw new Error(response.error || '处理失败');
        }
        
    } catch (error) {
        console.error('❌ URL处理失败:', error);
        
        result = {
            url: url,
            success: false,
            error: error.message,
            timestamp: new Date().toISOString(),
            processingTime: Date.now() - startTime
        };
        
        showProcessingResult(result);
        showAlert('danger', '处理失败', `URL "${url}" 处理失败: ${error.message}`);
    } finally {
        // 隐藏处理状态
        showProcessingStatus(false);
        setProcessingState(false);
        
        // 保存到历史记录
        if (result) {
            addToHistory(result);
        }
    }
}

/**
 * 处理批量URL提交
 */
async function handleBatchUrlsSubmit(event) {
    event.preventDefault();
    
    const urlsText = ELEMENTS.batchUrlsInput.value.trim();
    if (!urlsText) {
        showAlert('warning', '请输入URL', '请输入至少一个URL地址。');
        return;
    }
    
    const urls = urlsText.split('\n')
        .map(url => url.trim())
        .filter(url => url.length > 0);
    
    if (urls.length === 0) {
        showAlert('warning', '请输入有效URL', '请输入至少一个有效的URL地址。');
        return;
    }
    
    // 验证所有URL格式
    const invalidUrls = urls.filter(url => !isValidUrl(url));
    if (invalidUrls.length > 0) {
        showAlert('danger', 'URL格式错误', `以下URL格式不正确: ${invalidUrls.slice(0, 3).join(', ')}${invalidUrls.length > 3 ? '...' : ''}`);
        return;
    }
    
    await processBatchUrls(urls);
}

/**
 * 处理批量URL
 */
async function processBatchUrls(urls) {
    console.log(`📦 开始批量处理 ${urls.length} 个URL`);
    
    // 初始化批量处理状态
    STATE.batchProgress.current = 0;
    STATE.batchProgress.total = urls.length;
    STATE.batchProgress.results = [];
    
    // 显示批量处理状态
    showBatchProcessingStatus(true);
    updateBatchProgress();
    setProcessingState(true);
    
    const startTime = Date.now();
    
    try {
        // 调用批量处理API
        const response = await fetchAPI('/ingest/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ urls: urls })
        });
        
        // 处理批量结果
        if (response.results && Array.isArray(response.results)) {
            STATE.batchProgress.results = response.results.map((result, index) => ({
                ...result,
                url: urls[index],
                timestamp: new Date().toISOString()
            }));
            
            STATE.batchProgress.current = STATE.batchProgress.total;
            updateBatchProgress();
            
            // 显示批量结果
            showBatchResults(STATE.batchProgress.results);
            
            // 统计结果
            const successCount = STATE.batchProgress.results.filter(r => r.success).length;
            const failureCount = STATE.batchProgress.results.length - successCount;
            
            if (successCount === STATE.batchProgress.total) {
                showAlert('success', '批量处理完成', `所有 ${successCount} 个URL都已成功处理。`);
            } else if (successCount > 0) {
                showAlert('warning', '批量处理完成', `${successCount} 个URL成功，${failureCount} 个URL失败。`);
            } else {
                showAlert('danger', '批量处理失败', `所有 ${failureCount} 个URL都处理失败。`);
            }
            
            // 添加到历史记录
            STATE.batchProgress.results.forEach(result => addToHistory(result));
            
        } else {
            throw new Error('批量处理API返回格式错误');
        }
        
    } catch (error) {
        console.error('❌ 批量处理失败:', error);
        showAlert('danger', '批量处理失败', `批量处理过程中发生错误: ${error.message}`);
        
        // 记录失败结果
        urls.forEach(url => {
            addToHistory({
                url: url,
                success: false,
                error: error.message,
                timestamp: new Date().toISOString(),
                processingTime: 0
            });
        });
        
    } finally {
        showBatchProcessingStatus(false);
        setProcessingState(false);
        
        console.log(`📊 批量处理完成，耗时: ${Date.now() - startTime}ms`);
    }
}

/**
 * 显示处理状态
 */
function showProcessingStatus(show) {
    if (ELEMENTS.singleUrlStatus) {
        ELEMENTS.singleUrlStatus.classList.toggle('d-none', !show);
    }
    
    if (ELEMENTS.singleUrlResult) {
        ELEMENTS.singleUrlResult.classList.toggle('d-none', show);
    }
}

/**
 * 更新处理阶段
 */
function updateProcessingStage(stage) {
    if (ELEMENTS.singleUrlStage) {
        ELEMENTS.singleUrlStage.textContent = stage;
    }
}

/**
 * 更新处理进度
 */
function updateProcessingProgress(percent) {
    if (ELEMENTS.singleUrlProgress) {
        ELEMENTS.singleUrlProgress.style.width = `${percent}%`;
    }
}

/**
 * 显示处理结果
 */
function showProcessingResult(result) {
    if (!ELEMENTS.singleUrlResult) return;
    
    const resultHtml = createResultHtml(result);
    ELEMENTS.singleUrlResult.innerHTML = resultHtml;
    ELEMENTS.singleUrlResult.classList.remove('d-none');
    ELEMENTS.singleUrlResult.classList.add('fade-in');
}

/**
 * 显示批量处理状态
 */
function showBatchProcessingStatus(show) {
    if (ELEMENTS.batchProcessingStatus) {
        ELEMENTS.batchProcessingStatus.classList.toggle('d-none', !show);
    }
    
    if (ELEMENTS.batchResults) {
        ELEMENTS.batchResults.classList.toggle('d-none', show);
    }
}

/**
 * 更新批量处理进度
 */
function updateBatchProgress() {
    const progress = (STATE.batchProgress.current / STATE.batchProgress.total) * 100;
    
    if (ELEMENTS.batchProgress) {
        ELEMENTS.batchProgress.style.width = `${progress}%`;
    }
    
    if (ELEMENTS.batchProcessed) {
        ELEMENTS.batchProcessed.textContent = STATE.batchProgress.current;
    }
    
    if (ELEMENTS.batchTotal) {
        ELEMENTS.batchTotal.textContent = STATE.batchProgress.total;
    }
    
    if (ELEMENTS.batchCurrentStatus) {
        if (STATE.batchProgress.current === 0) {
            ELEMENTS.batchCurrentStatus.textContent = '准备开始...';
        } else if (STATE.batchProgress.current < STATE.batchProgress.total) {
            ELEMENTS.batchCurrentStatus.textContent = `正在处理第 ${STATE.batchProgress.current + 1} 个URL...`;
        } else {
            ELEMENTS.batchCurrentStatus.textContent = '批量处理完成';
        }
    }
}

/**
 * 显示批量结果
 */
function showBatchResults(results) {
    if (!ELEMENTS.batchResults) return;
    
    const resultsHtml = results.map(result => createResultHtml(result, true)).join('');
    
    ELEMENTS.batchResults.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h6 class="card-title mb-0">
                    <i class="bi bi-list-check"></i>
                    批量处理结果 (${results.length} 项)
                </h6>
            </div>
            <div class="card-body">
                ${resultsHtml}
            </div>
        </div>
    `;
    
    ELEMENTS.batchResults.classList.remove('d-none');
    ELEMENTS.batchResults.classList.add('fade-in');
}

/**
 * 创建结果HTML
 */
function createResultHtml(result, isCompact = false) {
    const statusClass = result.success ? 'success' : 'danger';
    const statusIcon = result.success ? 'check-circle' : 'x-circle';
    const statusText = result.success ? '成功' : '失败';
    
    const processingTime = result.processingTime ? `${(result.processingTime / 1000).toFixed(2)}秒` : '未知';
    
    let detailsHtml = '';
    
    if (result.success && result.data) {
        detailsHtml = `
            <div class="mt-2">
                <strong>提取的信息:</strong>
                <ul class="list-unstyled mt-1">
                    ${result.data.extracted_data ? Object.entries(result.data.extracted_data)
                        .filter(([key, value]) => value && value.toString().trim())
                        .map(([key, value]) => `
                            <li><small><strong>${key}:</strong> ${escapeHtml(value.toString().substring(0, 100))}${value.toString().length > 100 ? '...' : ''}</small></li>
                        `).join('') : '<li><small>无提取数据</small></li>'}
                </ul>
                ${result.data.notion_page_url ? `
                    <a href="${result.data.notion_page_url}" target="_blank" class="btn btn-outline-primary btn-sm">
                        <i class="bi bi-box-arrow-up-right"></i>
                        查看Notion页面
                    </a>
                ` : ''}
            </div>
        `;
    } else if (!result.success && result.error) {
        detailsHtml = `
            <div class="mt-2">
                <small class="text-danger">
                    <strong>错误:</strong> ${escapeHtml(result.error)}
                </small>
            </div>
        `;
    }
    
    return `
        <div class="alert alert-${statusClass} result-card ${isCompact ? 'mb-2' : ''} result-${statusClass}">
            <div class="d-flex align-items-start">
                <i class="bi bi-${statusIcon} me-2 mt-1"></i>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong>${statusText}</strong>
                            <div class="small text-muted mt-1">
                                URL: <a href="${result.url}" target="_blank" class="text-muted">${escapeHtml(result.url.substring(0, 60))}${result.url.length > 60 ? '...' : ''}</a>
                            </div>
                        </div>
                        <div class="text-end">
                            <div class="small text-muted">
                                ${processingTime}
                            </div>
                            <div class="small text-muted timestamp">
                                ${formatTimestamp(result.timestamp)}
                            </div>
                        </div>
                    </div>
                    ${!isCompact ? detailsHtml : ''}
                </div>
            </div>
        </div>
    `;
}

/**
 * 更新URL数量统计
 */
function updateBatchUrlCount() {
    if (!ELEMENTS.batchUrlsInput || !ELEMENTS.batchUrlCount) return;
    
    const urlsText = ELEMENTS.batchUrlsInput.value.trim();
    const urls = urlsText.split('\n')
        .map(url => url.trim())
        .filter(url => url.length > 0);
    
    ELEMENTS.batchUrlCount.textContent = `URL数量: ${urls.length}`;
}

/**
 * 设置处理状态
 */
function setProcessingState(isProcessing) {
    STATE.isProcessing = isProcessing;
    
    // 禁用/启用提交按钮
    if (ELEMENTS.singleUrlSubmit) {
        ELEMENTS.singleUrlSubmit.disabled = isProcessing;
    }
    
    if (ELEMENTS.batchUrlsSubmit) {
        ELEMENTS.batchUrlsSubmit.disabled = isProcessing;
    }
}

/**
 * 添加到历史记录
 */
function addToHistory(result) {
    STATE.processingHistory.unshift(result);
    
    // 限制历史记录数量
    if (STATE.processingHistory.length > 100) {
        STATE.processingHistory = STATE.processingHistory.slice(0, 100);
    }
    
    // 保存到localStorage
    localStorage.setItem('processingHistory', JSON.stringify(STATE.processingHistory));
    
    // 更新结果显示
    loadProcessingHistory();
}

/**
 * 加载处理历史
 */
function loadProcessingHistory() {
    if (!ELEMENTS.resultsContainer) return;
    
    if (STATE.processingHistory.length === 0) {
        ELEMENTS.resultsContainer.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="bi bi-inbox display-4"></i>
                <p class="mt-2">暂无处理记录</p>
                <p class="small">开始处理URL后，结果将显示在这里</p>
            </div>
        `;
        return;
    }
    
    const resultsHtml = STATE.processingHistory
        .slice(0, 20) // 只显示最近20条
        .map(result => createResultHtml(result, true))
        .join('');
    
    ELEMENTS.resultsContainer.innerHTML = `
        <div class="mb-3">
            <small class="text-muted">显示最近 ${Math.min(STATE.processingHistory.length, 20)} 条记录</small>
        </div>
        ${resultsHtml}
    `;
}

/**
 * 处理标签页切换
 */
function handleTabSwitch(tabId) {
    switch (tabId) {
        case 'system-info':
            loadSystemInfo();
            break;
        case 'results':
            loadProcessingHistory();
            break;
    }
}



/**
 * 工具函数 - API请求
 */
async function fetchAPI(endpoint, options = {}) {
    const url = `${CONFIG.API_BASE_URL}${endpoint}`;
    
    const defaultOptions = {
        timeout: CONFIG.TIMEOUT,
        headers: {
            'Accept': 'application/json',
            ...options.headers
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    console.log(`🌐 API请求: ${finalOptions.method || 'GET'} ${url}`);
    console.log(`🔧 配置信息:`, {
        API_BASE_URL: CONFIG.API_BASE_URL,
        currentOrigin: window.location.origin,
        currentHref: window.location.href
    });
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), finalOptions.timeout);
    
    try {
        const response = await fetch(url, {
            ...finalOptions,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        console.log(`📡 响应状态: ${response.status} ${response.statusText}`);
        console.log(`📡 响应头:`, Object.fromEntries(response.headers.entries()));
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`✅ API响应成功: ${endpoint}`, data);
        
        return data;
        
    } catch (error) {
        clearTimeout(timeoutId);
        
        if (error.name === 'AbortError') {
            throw new Error('请求超时');
        }
        
        console.error(`❌ API请求失败: ${endpoint}`, error);
        console.error(`❌ 错误详情:`, {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        throw error;
    }
}

/**
 * 工具函数 - URL验证
 */
function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (_) {
        return false;
    }
}

/**
 * 工具函数 - HTML转义
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

/**
 * 工具函数 - 时间格式化
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) {
        return '刚刚';
    } else if (diffMins < 60) {
        return `${diffMins}分钟前`;
    } else if (diffHours < 24) {
        return `${diffHours}小时前`;
    } else if (diffDays < 7) {
        return `${diffDays}天前`;
    } else {
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

/**
 * 工具函数 - 显示警告
 */
function showAlert(type, title, message, duration = 5000) {
    if (!ELEMENTS.alertContainer) return;
    
    const alertId = `alert-${Date.now()}`;
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <strong>${title}:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    ELEMENTS.alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // 自动消失
    if (duration > 0) {
        setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                const alert = new bootstrap.Alert(alertElement);
                alert.close();
            }
        }, duration);
    }
}

/**
 * 全局函数 - 刷新系统状态
 */
window.refreshSystemStatus = function() {
    initializeSystem();
};

/**
 * 全局函数 - 加载批量示例
 */
window.loadBatchExample = function() {
    if (ELEMENTS.batchUrlsInput) {
        const exampleUrls = [
            'https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822',
            'https://www.example.com/job1',
            'https://www.example.com/job2'
        ];
        
        ELEMENTS.batchUrlsInput.value = exampleUrls.join('\n');
        updateBatchUrlCount();
    }
};

/**
 * 全局函数 - 导出结果
 */
window.exportResults = function() {
    if (STATE.processingHistory.length === 0) {
        showAlert('warning', '无数据', '没有可导出的处理结果。');
        return;
    }
    
    const data = {
        exportTime: new Date().toISOString(),
        totalRecords: STATE.processingHistory.length,
        results: STATE.processingHistory
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `url-processing-results-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showAlert('success', '导出成功', '处理结果已导出为JSON文件。');
};

/**
 * 全局函数 - 清空结果
 */
window.clearResults = function() {
    if (STATE.processingHistory.length === 0) {
        showAlert('info', '无数据', '没有需要清空的记录。');
        return;
    }
    
    if (confirm(`确定要清空所有 ${STATE.processingHistory.length} 条处理记录吗？此操作不可撤销。`)) {
        STATE.processingHistory = [];
        localStorage.removeItem('processingHistory');
        loadProcessingHistory();
        showAlert('success', '清空成功', '所有处理记录已清空。');
    }
};

// 全局错误处理
window.addEventListener('error', function(event) {
    console.error('💥 全局错误:', event.error);
    showAlert('danger', '系统错误', '发生了意外错误，请刷新页面重试。');
});

// 全局未处理的Promise拒绝
window.addEventListener('unhandledrejection', function(event) {
    console.error('💥 未处理的Promise拒绝:', event.reason);
    showAlert('warning', '网络错误', '网络请求失败，请检查网络连接。');
});

/**
 * 设置相关函数
 */

/**
 * 处理设置表单提交
 */
async function handleSettingsSubmit(event) {
    event.preventDefault();
    
    const settings = {
        qwen_api_key: ELEMENTS.qwenApiKey.value.trim(),
        notion_api_key: ELEMENTS.notionApiKey.value.trim(),
        notion_database_id: ELEMENTS.notionDatabaseId.value.trim()
    };
    
    try {
        await saveSettings(settings);
        showAlert('success', '设置保存成功', 'API设置已成功保存。');
    } catch (error) {
        console.error('❌ 保存设置失败:', error);
        showAlert('danger', '保存失败', '设置保存失败: ' + error.message);
    }
}

/**
 * 保存设置到后端
 */
async function saveSettings(settings) {
    const response = await fetchAPI('/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    });
    
    if (!response.success) {
        throw new Error(response.message || '保存失败');
    }
    
    return response;
}

/**
 * 加载设置
 */
async function loadSettings() {
    try {
        // 加载健康状态
        if (ELEMENTS.healthStatus) {
            ELEMENTS.healthStatus.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p class="mt-2">检查系统状态中...</p></div>';
            
            const healthResponse = await fetchAPI('/health');
            
            const healthHtml = `
                <div class="list-group">
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <span>系统状态</span>
                        <span class="badge bg-${healthResponse.status === 'healthy' ? 'success' : 'danger'} rounded-pill">
                            ${healthResponse.status === 'healthy' ? '正常' : '异常'}
                        </span>
                    </div>
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <span>API版本</span>
                        <span class="text-muted">${healthResponse.version || '未知'}</span>
                    </div>
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <span>检查时间</span>
                        <span class="text-muted timestamp">${formatTimestamp(new Date().toISOString())}</span>
                    </div>
                </div>
            `;
            
            ELEMENTS.healthStatus.innerHTML = healthHtml;
        }
        
        // 加载当前设置
        const settingsResponse = await fetchAPI('/settings');
        
        if (settingsResponse.success) {
            const settings = settingsResponse.data || {};
            
            // 填充表单字段（API Key显示为点状）
            if (ELEMENTS.qwenApiKey) {
                ELEMENTS.qwenApiKey.value = settings.qwen_api_key ? '••••••••••••••••' : '';
            }
            if (ELEMENTS.notionApiKey) {
                ELEMENTS.notionApiKey.value = settings.notion_api_key ? '••••••••••••••••' : '';
            }
            if (ELEMENTS.notionDatabaseId) {
                ELEMENTS.notionDatabaseId.value = settings.notion_database_id || '';
            }
        }
        
    } catch (error) {
        console.error('❌ 加载设置失败:', error);
        
        if (ELEMENTS.healthStatus) {
            ELEMENTS.healthStatus.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    无法加载系统状态: ${error.message}
                </div>
            `;
        }
        
        showAlert('warning', '加载设置失败', '无法加载当前设置，请检查网络连接。');
    }
}

/**
 * 测试设置连接
 */
async function testSettings() {
    const settings = {
        qwen_api_key: ELEMENTS.qwenApiKey.value.trim(),
        notion_api_key: ELEMENTS.notionApiKey.value.trim(),
        notion_database_id: ELEMENTS.notionDatabaseId.value.trim()
    };
    
    try {
        showAlert('info', '测试连接中', '正在测试API连接，请稍候...');
        
        const response = await fetchAPI('/settings/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.success) {
            showAlert('success', '连接测试成功', '所有API连接测试通过！');
        } else {
            showAlert('danger', '连接测试失败', response.message || '连接测试失败');
        }
        
    } catch (error) {
        console.error('❌ 连接测试失败:', error);
        showAlert('danger', '连接测试失败', '连接测试失败: ' + error.message);
    }
}

/**
 * 切换密码可见性
 */
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const button = input.nextElementSibling;
    const icon = button.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'bi bi-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'bi bi-eye';
    }
}

/**
 * 全局函数 - 加载设置
 */
window.loadSettings = function() {
    loadSettings();
};

/**
 * 全局函数 - 测试设置
 */
window.testSettings = function() {
    testSettings();
};

/**
 * 全局函数 - 切换密码可见性
 */
window.togglePasswordVisibility = function(inputId) {
    togglePasswordVisibility(inputId);
};

console.log('📱 Web界面JavaScript模块加载完成');
