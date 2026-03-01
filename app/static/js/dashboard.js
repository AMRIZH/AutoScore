/**
 * Dashboard JavaScript for AutoScoring Application
 * Supports both Bulk Processing and Single Processing modes
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeTooltips(document);

    // ==================== BULK PROCESSING ELEMENTS ====================
    const uploadForm = document.getElementById('uploadForm');
    const studentUploadZone = document.getElementById('studentUploadZone');
    const studentFiles = document.getElementById('studentFiles');
    const studentFileList = document.getElementById('studentFileList');
    const answerKeyUploadZone = document.getElementById('answerKeyUploadZone');
    const answerKeyFile = document.getElementById('answerKeyFile');
    const answerKeyFileName = document.getElementById('answerKeyFileName');
    const questionDocUploadZone = document.getElementById('questionDocUploadZone');
    const questionDocFiles = document.getElementById('questionDocFiles');
    const questionDocFileList = document.getElementById('questionDocFileList');
    const additionalNotes = document.getElementById('additionalNotes');
    const submitBtn = document.getElementById('submitBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressMessage = document.getElementById('progressMessage');
    const resultContainer = document.getElementById('resultContainer');
    const resultAlert = document.getElementById('resultAlert');
    const resultMessage = document.getElementById('resultMessage');
    const downloadBtn = document.getElementById('downloadBtn');
    const newScoringBtn = document.getElementById('newScoringBtn');

    // ==================== SINGLE PROCESSING ELEMENTS ====================
    const singleUploadForm = document.getElementById('singleUploadForm');
    const singleQuestionDocUploadZone = document.getElementById('singleQuestionDocUploadZone');
    const singleQuestionDocFiles = document.getElementById('singleQuestionDocFiles');
    const singleQuestionDocFileList = document.getElementById('singleQuestionDocFileList');
    const singleAnswerKeyUploadZone = document.getElementById('singleAnswerKeyUploadZone');
    const singleAnswerKeyFile = document.getElementById('singleAnswerKeyFile');
    const singleAnswerKeyFileName = document.getElementById('singleAnswerKeyFileName');
    const singleAdditionalNotes = document.getElementById('singleAdditionalNotes');
    const addStudentBtn = document.getElementById('addStudentBtn');
    const studentTableBody = document.getElementById('studentTableBody');
    const singleSubmitBtn = document.getElementById('singleSubmitBtn');
    const singleProgressContainer = document.getElementById('singleProgressContainer');
    const singleProgressBar = document.getElementById('singleProgressBar');
    const singleProgressMessage = document.getElementById('singleProgressMessage');
    const singleResultContainer = document.getElementById('singleResultContainer');
    const singleResultAlert = document.getElementById('singleResultAlert');
    const singleResultMessage = document.getElementById('singleResultMessage');
    const singleDownloadBtn = document.getElementById('singleDownloadBtn');
    const singleNewScoringBtn = document.getElementById('singleNewScoringBtn');

    // ==================== STATE ====================
    // Bulk Processing State
    let selectedStudentFiles = [];
    let selectedQuestionDocs = [];

    // Single Processing State
    let singleSelectedQuestionDocs = [];
    let singleStudents = [];
    let studentIdCounter = 0;

    // Allowed extensions for question documents
    const questionDocExtensions = [
        'pdf', 'doc', 'docx', 'md', 'txt', 'markdown',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif',
        'tiff', 'tif'
    ];

    // ==================== BULK PROCESSING HANDLERS ====================

    // Student files upload zone
    if (studentUploadZone && studentFiles) {
        studentUploadZone.addEventListener('click', () => studentFiles.click());
        studentUploadZone.addEventListener('dragover', handleDragOver);
        studentUploadZone.addEventListener('dragleave', handleDragLeave);
        studentUploadZone.addEventListener('drop', handleStudentDrop);
        studentFiles.addEventListener('change', handleStudentFileSelect);
    }

    // Answer key upload zone
    if (answerKeyUploadZone && answerKeyFile) {
        answerKeyUploadZone.addEventListener('click', () => answerKeyFile.click());
        answerKeyUploadZone.addEventListener('dragover', handleDragOver);
        answerKeyUploadZone.addEventListener('dragleave', handleDragLeave);
        answerKeyUploadZone.addEventListener('drop', handleAnswerKeyDrop);
        answerKeyFile.addEventListener('change', handleAnswerKeySelect);
    }

    // Question document upload zone
    if (questionDocUploadZone && questionDocFiles) {
        questionDocUploadZone.addEventListener('click', () => questionDocFiles.click());
        questionDocUploadZone.addEventListener('dragover', handleDragOver);
        questionDocUploadZone.addEventListener('dragleave', handleDragLeave);
        questionDocUploadZone.addEventListener('drop', handleQuestionDocDrop);
        questionDocFiles.addEventListener('change', handleQuestionDocSelect);
    }

    // Form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmit);
    }

    // New scoring button
    if (newScoringBtn) {
        newScoringBtn.addEventListener('click', resetForm);
    }

    // ==================== SINGLE PROCESSING HANDLERS ====================

    // Single Question document upload zone
    if (singleQuestionDocUploadZone && singleQuestionDocFiles) {
        singleQuestionDocUploadZone.addEventListener('click', () => singleQuestionDocFiles.click());
        singleQuestionDocUploadZone.addEventListener('dragover', handleDragOver);
        singleQuestionDocUploadZone.addEventListener('dragleave', handleDragLeave);
        singleQuestionDocUploadZone.addEventListener('drop', handleSingleQuestionDocDrop);
        singleQuestionDocFiles.addEventListener('change', handleSingleQuestionDocSelect);
    }

    // Single Answer key upload zone
    if (singleAnswerKeyUploadZone && singleAnswerKeyFile) {
        singleAnswerKeyUploadZone.addEventListener('click', () => singleAnswerKeyFile.click());
        singleAnswerKeyUploadZone.addEventListener('dragover', handleDragOver);
        singleAnswerKeyUploadZone.addEventListener('dragleave', handleDragLeave);
        singleAnswerKeyUploadZone.addEventListener('drop', handleSingleAnswerKeyDrop);
        singleAnswerKeyFile.addEventListener('change', handleSingleAnswerKeySelect);
    }

    // Add student button
    if (addStudentBtn) {
        addStudentBtn.addEventListener('click', addStudent);
        // Add first student row by default
        addStudent();
    }

    // Single form submission
    if (singleUploadForm) {
        singleUploadForm.addEventListener('submit', handleSingleFormSubmit);
    }

    // Single new scoring button
    if (singleNewScoringBtn) {
        singleNewScoringBtn.addEventListener('click', resetSingleForm);
    }

    // ==================== COMMON DRAG/DROP HANDLERS ====================

    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.add('dragover');
    }

    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
    }

    // ==================== BULK PROCESSING FUNCTIONS ====================

    function handleStudentDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
        if (files.length > 0) {
            addStudentFiles(files);
        }
    }

    function handleAnswerKeyDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
        if (files.length > 0) {
            setAnswerKeyFile(files[0]);
        }
    }

    function handleQuestionDocDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files).filter(f => isAllowedQuestionDoc(f));
        if (files.length > 0) {
            addQuestionDocs(files);
        }
    }

    function isAllowedQuestionDoc(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        return questionDocExtensions.includes(ext);
    }

    function handleStudentFileSelect(e) {
        const files = Array.from(e.target.files);
        addStudentFiles(files);
    }

    function handleAnswerKeySelect(e) {
        if (e.target.files.length > 0) {
            setAnswerKeyFile(e.target.files[0]);
        }
    }

    function handleQuestionDocSelect(e) {
        const files = Array.from(e.target.files);
        addQuestionDocs(files);
    }

    function addStudentFiles(files) {
        files.forEach(file => {
            if (!selectedStudentFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedStudentFiles.push(file);
            }
        });

        updateStudentFileList();
        updateUploadZoneState();
    }

    function addQuestionDocs(files) {
        const remainingSlots = 10 - selectedQuestionDocs.length;
        const filesToAdd = files.slice(0, remainingSlots);

        filesToAdd.forEach(file => {
            if (!selectedQuestionDocs.some(f => f.name === file.name && f.size === file.size)) {
                selectedQuestionDocs.push(file);
            }
        });

        if (files.length > remainingSlots) {
            alert(`Hanya ${remainingSlots} file yang dapat ditambahkan. Maksimal 10 file dokumen soal.`);
        }

        updateQuestionDocFileList();
        updateQuestionDocUploadZoneState();
    }

    function updateStudentFileList() {
        studentFileList.innerHTML = '';

        if (selectedStudentFiles.length === 0) {
            return;
        }

        const countBadge = document.createElement('div');
        countBadge.className = 'mb-2';
        countBadge.innerHTML = `<span class="badge bg-primary">${selectedStudentFiles.length} file dipilih</span>`;
        studentFileList.appendChild(countBadge);

        selectedStudentFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';

            const fileNameSpan = document.createElement('span');
            fileNameSpan.className = 'file-name';
            fileNameSpan.title = file.name;

            const icon = document.createElement('i');
            icon.className = 'bi bi-file-earmark-pdf text-danger me-2';
            fileNameSpan.appendChild(icon);
            fileNameSpan.appendChild(document.createTextNode(file.name));

            const removeSpan = document.createElement('span');
            removeSpan.className = 'remove-file';
            removeSpan.dataset.index = index;
            removeSpan.title = 'Hapus';

            const removeIcon = document.createElement('i');
            removeIcon.className = 'bi bi-x-circle';
            removeSpan.appendChild(removeIcon);

            fileItem.appendChild(fileNameSpan);
            fileItem.appendChild(removeSpan);
            studentFileList.appendChild(fileItem);
        });

        document.querySelectorAll('#studentFileList .remove-file').forEach(btn => {
            btn.addEventListener('click', function () {
                const index = parseInt(this.dataset.index);
                selectedStudentFiles.splice(index, 1);
                updateStudentFileList();
                updateUploadZoneState();
            });
        });
    }

    function updateQuestionDocFileList() {
        if (!questionDocFileList) return;

        questionDocFileList.innerHTML = '';

        if (selectedQuestionDocs.length === 0) {
            return;
        }

        const countBadge = document.createElement('div');
        countBadge.className = 'mb-2';
        countBadge.innerHTML = `<span class="badge bg-info">${selectedQuestionDocs.length}/10 file dokumen soal</span>`;
        questionDocFileList.appendChild(countBadge);

        selectedQuestionDocs.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            const ext = file.name.split('.').pop().toLowerCase();
            const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif', 'tiff', 'tif'].includes(ext);
            const iconClass = isImage ? 'bi-file-earmark-image text-success' :
                (ext === 'pdf' ? 'bi-file-earmark-pdf text-danger' : 'bi-file-earmark-word text-primary');

            const fileNameSpan = document.createElement('span');
            fileNameSpan.className = 'file-name';
            fileNameSpan.title = file.name;

            const icon = document.createElement('i');
            icon.className = `bi ${iconClass} me-2`;
            fileNameSpan.appendChild(icon);
            fileNameSpan.appendChild(document.createTextNode(file.name));

            const removeSpan = document.createElement('span');
            removeSpan.className = 'remove-question-doc';
            removeSpan.dataset.index = index;
            removeSpan.title = 'Hapus';

            const removeIcon = document.createElement('i');
            removeIcon.className = 'bi bi-x-circle';
            removeSpan.appendChild(removeIcon);

            fileItem.appendChild(fileNameSpan);
            fileItem.appendChild(removeSpan);
            questionDocFileList.appendChild(fileItem);
        });

        document.querySelectorAll('#questionDocFileList .remove-question-doc').forEach(btn => {
            btn.addEventListener('click', function () {
                const index = parseInt(this.dataset.index);
                selectedQuestionDocs.splice(index, 1);
                updateQuestionDocFileList();
                updateQuestionDocUploadZoneState();
            });
        });
    }

    function updateUploadZoneState() {
        if (selectedStudentFiles.length > 0) {
            studentUploadZone.classList.add('has-files');
        } else {
            studentUploadZone.classList.remove('has-files');
        }
    }

    function updateQuestionDocUploadZoneState() {
        if (!questionDocUploadZone) return;

        if (selectedQuestionDocs.length > 0) {
            questionDocUploadZone.classList.add('has-files');
        } else {
            questionDocUploadZone.classList.remove('has-files');
        }
    }

    function setAnswerKeyFile(file) {
        answerKeyFileName.innerHTML = '';

        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';

        const fileNameSpan = document.createElement('span');
        fileNameSpan.className = 'file-name';
        fileNameSpan.title = file.name;

        const icon = document.createElement('i');
        icon.className = 'bi bi-file-earmark-check text-success me-2';
        fileNameSpan.appendChild(icon);
        fileNameSpan.appendChild(document.createTextNode(file.name));

        const removeSpan = document.createElement('span');
        removeSpan.className = 'remove-answer-key';
        removeSpan.title = 'Hapus';

        const removeIcon = document.createElement('i');
        removeIcon.className = 'bi bi-x-circle';
        removeSpan.appendChild(removeIcon);

        fileItem.appendChild(fileNameSpan);
        fileItem.appendChild(removeSpan);
        answerKeyFileName.appendChild(fileItem);

        answerKeyUploadZone.classList.add('has-files');

        document.querySelector('.remove-answer-key').addEventListener('click', function () {
            answerKeyFile.value = '';
            answerKeyFileName.innerHTML = '';
            answerKeyUploadZone.classList.remove('has-files');
        });
    }

    async function handleFormSubmit(e) {
        e.preventDefault();

        const readiness = await checkLlmReadiness();
        if (!readiness.ready) {
            alert(readiness.message || 'Konfigurasi LLM belum siap. Hubungi admin.');
            return;
        }

        if (selectedStudentFiles.length === 0) {
            alert('Silakan pilih file laporan mahasiswa terlebih dahulu.');
            return;
        }

        const scoreMin = parseInt(document.getElementById('scoreMin').value);
        const scoreMax = parseInt(document.getElementById('scoreMax').value);

        if (scoreMin >= scoreMax) {
            alert('Nilai minimum harus lebih kecil dari nilai maksimum.');
            return;
        }

        // Validate at least one reference is provided
        const hasAnswerKey = answerKeyFile && answerKeyFile.files.length > 0;
        const hasQuestionDocs = selectedQuestionDocs.length > 0;
        const hasAdditionalNotes = additionalNotes && additionalNotes.value.trim().length > 0;

        if (!hasAnswerKey && !hasQuestionDocs && !hasAdditionalNotes) {
            alert('Minimal satu referensi harus diisi:\n• Kunci Jawaban, atau\n• Dokumen Soal/Tugas, atau\n• Catatan Tambahan');
            return;
        }

        const formData = new FormData();
        formData.append('csrf_token', document.querySelector('[name=csrf_token]').value);
        formData.append('score_min', scoreMin);
        formData.append('score_max', scoreMax);
        formData.append('enable_evaluation', document.getElementById('enableEvaluation').checked);

        selectedStudentFiles.forEach(file => {
            formData.append('student_files', file);
        });

        if (answerKeyFile.files.length > 0) {
            formData.append('answer_key', answerKeyFile.files[0]);
        }

        selectedQuestionDocs.forEach(file => {
            formData.append('question_documents', file);
        });

        if (additionalNotes && additionalNotes.value.trim()) {
            formData.append('additional_notes', additionalNotes.value.trim());
        }

        setFormDisabled(true);
        showProgress();

        try {
            updateProgress(0, 'Mengunggah dokumen...');

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Terjadi kesalahan saat mengunggah file.');
            }

            const jobId = result.job_id;
            listenToProgress(jobId);

        } catch (error) {
            console.error('Upload error:', error);
            showError(error.message);
            setFormDisabled(false);
            hideProgress();
        }
    }

    function listenToProgress(jobId) {
        const eventSource = new EventSource(`/api/progress/${jobId}`);

        eventSource.onmessage = function (event) {
            const data = JSON.parse(event.data);

            updateProgress(data.progress, data.message);

            if (data.status === 'completed') {
                eventSource.close();
                showResult(jobId, data.message);
            } else if (data.status === 'failed' || data.status === 'error') {
                eventSource.close();
                showError(data.message);
                setFormDisabled(false);
            }
        };

        eventSource.onerror = function (error) {
            console.error('SSE error:', error);
            eventSource.close();
            pollProgress(jobId);
        };
    }

    async function pollProgress(jobId) {
        const checkProgress = async () => {
            try {
                const response = await fetch(`/api/job/${jobId}`);
                const data = await response.json();

                if (!data.success) {
                    throw new Error(data.error);
                }

                const job = data.job;
                const progress = (job.processed_files / job.total_files) * 100;
                updateProgress(progress, job.status_message || 'Memproses...');

                if (job.status === 'completed') {
                    showResult(jobId, `Berhasil menilai ${job.total_files} laporan.`);
                } else if (job.status === 'failed') {
                    showError(job.status_message || 'Terjadi kesalahan.');
                    setFormDisabled(false);
                } else {
                    setTimeout(checkProgress, 2000);
                }
            } catch (error) {
                console.error('Poll error:', error);
                showError('Gagal memantau progress. Silakan refresh halaman.');
                setFormDisabled(false);
            }
        };

        checkProgress();
    }

    function updateProgress(percent, message) {
        progressBar.style.width = `${percent}%`;
        progressBar.textContent = `${Math.round(percent)}%`;
        progressMessage.textContent = message;
    }

    function showProgress() {
        progressContainer.classList.add('active');
        resultContainer.classList.remove('active');
    }

    function hideProgress() {
        progressContainer.classList.remove('active');
    }

    function showResult(jobId, message) {
        hideProgress();

        resultAlert.className = 'alert alert-success';
        resultAlert.querySelector('.alert-heading').innerHTML = '<i class="bi bi-check-circle me-2"></i>Penilaian Selesai!';
        resultMessage.textContent = message;
        downloadBtn.href = `/api/download/${jobId}`;

        resultContainer.classList.add('active');
        setFormDisabled(false);
    }

    function showError(message) {
        hideProgress();

        resultAlert.className = 'alert alert-danger';
        resultAlert.querySelector('.alert-heading').innerHTML = '<i class="bi bi-exclamation-circle me-2"></i>Terjadi Kesalahan';
        resultMessage.textContent = message;
        downloadBtn.style.display = 'none';

        resultContainer.classList.add('active');
    }

    function setFormDisabled(disabled) {
        submitBtn.disabled = disabled;
        studentFiles.disabled = disabled;
        answerKeyFile.disabled = disabled;
        if (questionDocFiles) questionDocFiles.disabled = disabled;
        if (additionalNotes) additionalNotes.disabled = disabled;
        document.getElementById('scoreMin').disabled = disabled;
        document.getElementById('scoreMax').disabled = disabled;
        document.getElementById('enableEvaluation').disabled = disabled;

        if (disabled) {
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Memproses...';
            studentUploadZone.style.pointerEvents = 'none';
            answerKeyUploadZone.style.pointerEvents = 'none';
            if (questionDocUploadZone) questionDocUploadZone.style.pointerEvents = 'none';
        } else {
            submitBtn.innerHTML = '<i class="bi bi-play-circle me-2"></i>Mulai Penilaian';
            studentUploadZone.style.pointerEvents = 'auto';
            answerKeyUploadZone.style.pointerEvents = 'auto';
            if (questionDocUploadZone) questionDocUploadZone.style.pointerEvents = 'auto';
        }
    }

    function resetForm() {
        selectedStudentFiles = [];
        selectedQuestionDocs = [];
        studentFiles.value = '';
        answerKeyFile.value = '';
        if (questionDocFiles) questionDocFiles.value = '';
        if (additionalNotes) additionalNotes.value = '';

        studentFileList.innerHTML = '';
        answerKeyFileName.innerHTML = '';
        if (questionDocFileList) questionDocFileList.innerHTML = '';
        studentUploadZone.classList.remove('has-files');
        answerKeyUploadZone.classList.remove('has-files');
        if (questionDocUploadZone) questionDocUploadZone.classList.remove('has-files');

        resultContainer.classList.remove('active');
        downloadBtn.style.display = '';

        updateProgress(0, 'Mempersiapkan...');

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ==================== SINGLE PROCESSING FUNCTIONS ====================

    function handleSingleQuestionDocDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files).filter(f => isAllowedQuestionDoc(f));
        if (files.length > 0) {
            addSingleQuestionDocs(files);
        }
    }

    function handleSingleQuestionDocSelect(e) {
        const files = Array.from(e.target.files);
        addSingleQuestionDocs(files);
    }

    function handleSingleAnswerKeyDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
        if (files.length > 0) {
            setSingleAnswerKeyFile(files[0]);
        }
    }

    function handleSingleAnswerKeySelect(e) {
        if (e.target.files.length > 0) {
            setSingleAnswerKeyFile(e.target.files[0]);
        }
    }

    function addSingleQuestionDocs(files) {
        const remainingSlots = 10 - singleSelectedQuestionDocs.length;
        const filesToAdd = files.slice(0, remainingSlots);

        filesToAdd.forEach(file => {
            if (!singleSelectedQuestionDocs.some(f => f.name === file.name && f.size === file.size)) {
                singleSelectedQuestionDocs.push(file);
            }
        });

        if (files.length > remainingSlots) {
            alert(`Hanya ${remainingSlots} file yang dapat ditambahkan. Maksimal 10 file dokumen soal.`);
        }

        updateSingleQuestionDocFileList();
        updateSingleQuestionDocUploadZoneState();
    }

    function updateSingleQuestionDocFileList() {
        if (!singleQuestionDocFileList) return;

        singleQuestionDocFileList.innerHTML = '';

        if (singleSelectedQuestionDocs.length === 0) {
            return;
        }

        const countBadge = document.createElement('div');
        countBadge.className = 'mb-2';
        countBadge.innerHTML = `<span class="badge bg-info">${singleSelectedQuestionDocs.length}/10 file dokumen soal</span>`;
        singleQuestionDocFileList.appendChild(countBadge);

        singleSelectedQuestionDocs.forEach((file, index) => {
            const fileItem = createFileItem(file, index, 'single-remove-question-doc');
            singleQuestionDocFileList.appendChild(fileItem);
        });

        document.querySelectorAll('#singleQuestionDocFileList .single-remove-question-doc').forEach(btn => {
            btn.addEventListener('click', function () {
                const index = parseInt(this.dataset.index);
                singleSelectedQuestionDocs.splice(index, 1);
                updateSingleQuestionDocFileList();
                updateSingleQuestionDocUploadZoneState();
            });
        });
    }

    function updateSingleQuestionDocUploadZoneState() {
        if (!singleQuestionDocUploadZone) return;

        if (singleSelectedQuestionDocs.length > 0) {
            singleQuestionDocUploadZone.classList.add('has-files');
        } else {
            singleQuestionDocUploadZone.classList.remove('has-files');
        }
    }

    function setSingleAnswerKeyFile(file) {
        singleAnswerKeyFileName.innerHTML = '';

        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';

        const fileNameSpan = document.createElement('span');
        fileNameSpan.className = 'file-name';
        fileNameSpan.title = file.name;

        const icon = document.createElement('i');
        icon.className = 'bi bi-file-earmark-check text-success me-2';
        fileNameSpan.appendChild(icon);
        fileNameSpan.appendChild(document.createTextNode(file.name));

        const removeSpan = document.createElement('span');
        removeSpan.className = 'single-remove-answer-key';
        removeSpan.title = 'Hapus';

        const removeIcon = document.createElement('i');
        removeIcon.className = 'bi bi-x-circle';
        removeSpan.appendChild(removeIcon);

        fileItem.appendChild(fileNameSpan);
        fileItem.appendChild(removeSpan);
        singleAnswerKeyFileName.appendChild(fileItem);

        singleAnswerKeyUploadZone.classList.add('has-files');

        document.querySelector('.single-remove-answer-key').addEventListener('click', function () {
            singleAnswerKeyFile.value = '';
            singleAnswerKeyFileName.innerHTML = '';
            singleAnswerKeyUploadZone.classList.remove('has-files');
        });
    }

    function createFileItem(file, index, removeClass) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        const ext = file.name.split('.').pop().toLowerCase();
        const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif', 'tiff', 'tif'].includes(ext);
        const iconClass = isImage ? 'bi-file-earmark-image text-success' :
            (ext === 'pdf' ? 'bi-file-earmark-pdf text-danger' : 'bi-file-earmark-word text-primary');

        const fileNameSpan = document.createElement('span');
        fileNameSpan.className = 'file-name';
        fileNameSpan.title = file.name;

        const icon = document.createElement('i');
        icon.className = `bi ${iconClass} me-2`;
        fileNameSpan.appendChild(icon);
        fileNameSpan.appendChild(document.createTextNode(file.name));

        const removeSpan = document.createElement('span');
        removeSpan.className = removeClass;
        removeSpan.dataset.index = index;
        removeSpan.title = 'Hapus';
        removeSpan.style.cursor = 'pointer';

        const removeIcon = document.createElement('i');
        removeIcon.className = 'bi bi-x-circle text-danger';
        removeSpan.appendChild(removeIcon);

        fileItem.appendChild(fileNameSpan);
        fileItem.appendChild(removeSpan);

        return fileItem;
    }

    // Add a new student row
    function addStudent() {
        studentIdCounter++;
        const studentId = studentIdCounter;

        const student = {
            id: studentId,
            files: [],
            status: 'pending', // pending, processing, completed, error
            result: null
        };
        singleStudents.push(student);

        const row = document.createElement('tr');
        row.className = 'student-row';
        row.dataset.studentId = studentId;

        row.innerHTML = `
            <td class="text-center align-middle">${singleStudents.length}</td>
            <td>
                <div class="upload-zone upload-zone-sm student-file-zone" data-student-id="${studentId}">
                    <i class="bi bi-file-earmark-plus text-muted"></i>
                    <span class="ms-1 small">Klik, seret file, atau </span>
                    <button type="button" class="btn btn-outline-secondary btn-sm btn-camera js-tooltip" data-student-id="${studentId}" title="Ambil jawaban langsung dari kamera perangkat.">
                        <i class="bi bi-camera"></i>
                    </button>
                    <input type="file" class="d-none student-file-input" 
                           multiple accept=".pdf,.docx,.doc,.md,.txt,image/*" data-student-id="${studentId}">
                </div>
                <div class="file-list mt-1 student-file-list" data-student-id="${studentId}"></div>
            </td>
            <td class="text-center align-middle">
                <div class="student-status" data-student-id="${studentId}">
                    <span class="badge bg-secondary">Menunggu</span>
                </div>
            </td>
            <td class="text-center align-middle">
                <button type="button" class="btn btn-success btn-sm btn-process-student js-tooltip" 
                    data-student-id="${studentId}" title="Proses penilaian untuk mahasiswa ini saja.">
                    <i class="bi bi-play-fill me-1"></i>Proses
                </button>
                <button type="button" class="btn btn-outline-danger btn-sm btn-remove-student ms-1 js-tooltip" 
                    data-student-id="${studentId}" title="Hapus baris mahasiswa dari daftar.">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;

        studentTableBody.appendChild(row);
        initializeTooltips(row);

        // Setup event listeners for this row
        setupStudentRowListeners(studentId);
    }

    function setupStudentRowListeners(studentId) {
        const row = document.querySelector(`tr[data-student-id="${studentId}"]`);

        // File zone click
        const fileZone = row.querySelector('.student-file-zone');
        const fileInput = row.querySelector('.student-file-input');

        fileZone.addEventListener('click', (e) => {
            // Don't trigger if clicking the camera button
            if (e.target.closest('.btn-camera')) return;
            fileInput.click();
        });
        fileZone.addEventListener('dragover', handleDragOver);
        fileZone.addEventListener('dragleave', handleDragLeave);
        fileZone.addEventListener('drop', function (e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('dragover');

            const files = Array.from(e.dataTransfer.files).filter(f => isAllowedQuestionDoc(f));
            if (files.length > 0) {
                addStudentFiles2(studentId, files);
            }
        });

        fileInput.addEventListener('change', function (e) {
            const files = Array.from(e.target.files);
            addStudentFiles2(studentId, files);
        });

        // Camera button
        row.querySelector('.btn-camera').addEventListener('click', function (e) {
            e.stopPropagation();
            openCameraModal(studentId);
        });

        // Process button
        row.querySelector('.btn-process-student').addEventListener('click', function () {
            processStudent(studentId);
        });

        // Remove button
        row.querySelector('.btn-remove-student').addEventListener('click', function () {
            removeStudent(studentId);
        });
    }

    function addStudentFiles2(studentId, files) {
        const student = singleStudents.find(s => s.id === studentId);
        if (!student) return;

        files.forEach(file => {
            if (!student.files.some(f => f.name === file.name && f.size === file.size)) {
                student.files.push(file);
            }
        });

        updateStudentFileList2(studentId);
    }

    function updateStudentFileList2(studentId) {
        const student = singleStudents.find(s => s.id === studentId);
        if (!student) return;

        const fileList = document.querySelector(`.student-file-list[data-student-id="${studentId}"]`);
        const fileZone = document.querySelector(`.student-file-zone[data-student-id="${studentId}"]`);

        fileList.innerHTML = '';

        if (student.files.length === 0) {
            fileZone.classList.remove('has-files');
            return;
        }

        fileZone.classList.add('has-files');

        student.files.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'd-flex justify-content-between align-items-center small py-1';

            const ext = file.name.split('.').pop().toLowerCase();
            const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif', 'tiff', 'tif'].includes(ext);
            const iconClass = isImage ? 'bi-file-earmark-image text-success' :
                (ext === 'pdf' ? 'bi-file-earmark-pdf text-danger' : 'bi-file-earmark-word text-primary');

            const nameSpan = document.createElement('span');
            nameSpan.className = 'text-truncate';
            nameSpan.style.maxWidth = '200px';
            nameSpan.title = file.name;
            nameSpan.innerHTML = `<i class="bi ${iconClass} me-1"></i>${file.name}`;

            const removeBtn = document.createElement('span');
            removeBtn.className = 'text-danger ms-2';
            removeBtn.style.cursor = 'pointer';
            removeBtn.innerHTML = '<i class="bi bi-x-circle"></i>';
            removeBtn.addEventListener('click', function () {
                student.files.splice(index, 1);
                updateStudentFileList2(studentId);
            });

            fileItem.appendChild(nameSpan);
            fileItem.appendChild(removeBtn);
            fileList.appendChild(fileItem);
        });
    }

    function removeStudent(studentId) {
        const index = singleStudents.findIndex(s => s.id === studentId);
        if (index > -1) {
            singleStudents.splice(index, 1);
        }

        const row = document.querySelector(`tr[data-student-id="${studentId}"]`);
        if (row) {
            disposeTooltipsIn(row);
            row.remove();
        }

        // Update row numbers
        updateStudentRowNumbers();
    }

    function updateStudentRowNumbers() {
        const rows = studentTableBody.querySelectorAll('tr');
        rows.forEach((row, index) => {
            row.querySelector('td:first-child').textContent = index + 1;
        });
    }

    async function handleSingleFormSubmit(e) {
        e.preventDefault();

        const readiness = await checkLlmReadiness();
        if (!readiness.ready) {
            alert(readiness.message || 'Konfigurasi LLM belum siap. Hubungi admin.');
            return;
        }

        // Validate students
        if (singleStudents.length === 0) {
            alert('Silakan tambahkan minimal satu mahasiswa.');
            return;
        }

        // Check each student has files
        for (let i = 0; i < singleStudents.length; i++) {
            const student = singleStudents[i];
            if (student.files.length === 0) {
                alert(`Silakan unggah file jawaban untuk mahasiswa nomor ${i + 1}.`);
                return;
            }
        }

        const scoreMin = parseInt(document.getElementById('singleScoreMin').value);
        const scoreMax = parseInt(document.getElementById('singleScoreMax').value);

        if (scoreMin >= scoreMax) {
            alert('Nilai minimum harus lebih kecil dari nilai maksimum.');
            return;
        }

        // Validate at least one reference is provided
        const hasAnswerKey = singleAnswerKeyFile && singleAnswerKeyFile.files.length > 0;
        const hasQuestionDocs = singleSelectedQuestionDocs.length > 0;
        const hasAdditionalNotes = singleAdditionalNotes && singleAdditionalNotes.value.trim().length > 0;

        if (!hasAnswerKey && !hasQuestionDocs && !hasAdditionalNotes) {
            alert('Minimal satu referensi harus diisi:\n• Kunci Jawaban, atau\n• Dokumen Soal/Tugas, atau\n• Catatan Tambahan');
            return;
        }

        // Build form data
        const formData = new FormData();
        formData.append('csrf_token', document.querySelector('#singleUploadForm [name=csrf_token]').value);
        formData.append('score_min', scoreMin);
        formData.append('score_max', scoreMax);
        formData.append('enable_evaluation', document.getElementById('singleEnableEvaluation').checked);

        // Add question documents
        singleSelectedQuestionDocs.forEach(file => {
            formData.append('question_documents', file);
        });

        // Add answer key
        if (singleAnswerKeyFile && singleAnswerKeyFile.files.length > 0) {
            formData.append('answer_key', singleAnswerKeyFile.files[0]);
        }

        // Add additional notes
        if (singleAdditionalNotes && singleAdditionalNotes.value.trim()) {
            formData.append('additional_notes', singleAdditionalNotes.value.trim());
        }

        // Add students data (just file count per student, NIM/Name will be extracted by LLM)
        const studentsData = singleStudents.map(s => ({
            fileCount: s.files.length
        }));
        formData.append('students_data', JSON.stringify(studentsData));

        // Add student files
        singleStudents.forEach((student, studentIndex) => {
            student.files.forEach((file, fileIndex) => {
                formData.append(`student_${studentIndex}_files`, file);
            });
        });

        setSingleFormDisabled(true);
        showSingleProgress();

        try {
            updateSingleProgress(0, 'Mengunggah dokumen...');

            const response = await fetch('/api/upload-single', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Terjadi kesalahan saat mengunggah file.');
            }

            const jobId = result.job_id;
            listenToSingleProgress(jobId);

        } catch (error) {
            console.error('Upload error:', error);
            showSingleError(error.message);
            setSingleFormDisabled(false);
            hideSingleProgress();
        }
    }

    function listenToSingleProgress(jobId) {
        const eventSource = new EventSource(`/api/progress/${jobId}`);

        eventSource.onmessage = function (event) {
            const data = JSON.parse(event.data);

            updateSingleProgress(data.progress, data.message);

            if (data.status === 'completed') {
                eventSource.close();
                showSingleResult(jobId, data.message);
            } else if (data.status === 'failed' || data.status === 'error') {
                eventSource.close();
                showSingleError(data.message);
                setSingleFormDisabled(false);
            }
        };

        eventSource.onerror = function (error) {
            console.error('SSE error:', error);
            eventSource.close();
            pollSingleProgress(jobId);
        };
    }

    async function pollSingleProgress(jobId) {
        const checkProgress = async () => {
            try {
                const response = await fetch(`/api/job/${jobId}`);
                const data = await response.json();

                if (!data.success) {
                    throw new Error(data.error);
                }

                const job = data.job;
                const progress = (job.processed_files / job.total_files) * 100;
                updateSingleProgress(progress, job.status_message || 'Memproses...');

                if (job.status === 'completed') {
                    showSingleResult(jobId, `Berhasil menilai ${job.total_files} mahasiswa.`);
                } else if (job.status === 'failed') {
                    showSingleError(job.status_message || 'Terjadi kesalahan.');
                    setSingleFormDisabled(false);
                } else {
                    setTimeout(checkProgress, 2000);
                }
            } catch (error) {
                console.error('Poll error:', error);
                showSingleError('Gagal memantau progress. Silakan refresh halaman.');
                setSingleFormDisabled(false);
            }
        };

        checkProgress();
    }

    function updateSingleProgress(percent, message) {
        singleProgressBar.style.width = `${percent}%`;
        singleProgressBar.textContent = `${Math.round(percent)}%`;
        singleProgressMessage.textContent = message;
    }

    function showSingleProgress() {
        singleProgressContainer.classList.add('active');
        singleResultContainer.classList.remove('active');
    }

    function hideSingleProgress() {
        singleProgressContainer.classList.remove('active');
    }

    function showSingleResult(jobId, message) {
        hideSingleProgress();

        singleResultAlert.className = 'alert alert-success';
        singleResultAlert.querySelector('.alert-heading').innerHTML = '<i class="bi bi-check-circle me-2"></i>Penilaian Selesai!';
        singleResultMessage.textContent = message;
        singleDownloadBtn.href = `/api/download/${jobId}`;

        singleResultContainer.classList.add('active');
        setSingleFormDisabled(false);
    }

    function showSingleError(message) {
        hideSingleProgress();

        singleResultAlert.className = 'alert alert-danger';
        singleResultAlert.querySelector('.alert-heading').innerHTML = '<i class="bi bi-exclamation-circle me-2"></i>Terjadi Kesalahan';
        singleResultMessage.textContent = message;
        singleDownloadBtn.style.display = 'none';

        singleResultContainer.classList.add('active');
    }

    function setSingleFormDisabled(disabled) {
        singleSubmitBtn.disabled = disabled;
        addStudentBtn.disabled = disabled;
        if (singleQuestionDocFiles) singleQuestionDocFiles.disabled = disabled;
        if (singleAnswerKeyFile) singleAnswerKeyFile.disabled = disabled;
        if (singleAdditionalNotes) singleAdditionalNotes.disabled = disabled;
        document.getElementById('singleScoreMin').disabled = disabled;
        document.getElementById('singleScoreMax').disabled = disabled;
        document.getElementById('singleEnableEvaluation').disabled = disabled;

        // Disable all student inputs
        document.querySelectorAll('.student-nim, .student-name, .student-file-input').forEach(el => {
            el.disabled = disabled;
        });
        document.querySelectorAll('.btn-remove-student').forEach(el => {
            el.disabled = disabled;
        });

        if (disabled) {
            singleSubmitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Memproses...';
            if (singleQuestionDocUploadZone) singleQuestionDocUploadZone.style.pointerEvents = 'none';
            if (singleAnswerKeyUploadZone) singleAnswerKeyUploadZone.style.pointerEvents = 'none';
            document.querySelectorAll('.student-file-zone').forEach(el => {
                el.style.pointerEvents = 'none';
            });
        } else {
            singleSubmitBtn.innerHTML = '<i class="bi bi-play-circle me-2"></i>Mulai Penilaian';
            if (singleQuestionDocUploadZone) singleQuestionDocUploadZone.style.pointerEvents = 'auto';
            if (singleAnswerKeyUploadZone) singleAnswerKeyUploadZone.style.pointerEvents = 'auto';
            document.querySelectorAll('.student-file-zone').forEach(el => {
                el.style.pointerEvents = 'auto';
            });
        }
    }

    function resetSingleForm() {
        // Reset state
        singleSelectedQuestionDocs = [];
        singleStudents = [];
        studentIdCounter = 0;

        // Clear file inputs
        if (singleQuestionDocFiles) singleQuestionDocFiles.value = '';
        if (singleAnswerKeyFile) singleAnswerKeyFile.value = '';
        if (singleAdditionalNotes) singleAdditionalNotes.value = '';

        // Clear displays
        if (singleQuestionDocFileList) singleQuestionDocFileList.innerHTML = '';
        if (singleAnswerKeyFileName) singleAnswerKeyFileName.innerHTML = '';
        if (singleQuestionDocUploadZone) singleQuestionDocUploadZone.classList.remove('has-files');
        if (singleAnswerKeyUploadZone) singleAnswerKeyUploadZone.classList.remove('has-files');

        // Clear student table
        studentTableBody.innerHTML = '';

        // Add first student row
        addStudent();

        // Hide result
        singleResultContainer.classList.remove('active');
        singleDownloadBtn.style.display = '';

        // Reset progress
        updateSingleProgress(0, 'Mempersiapkan...');

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ==================== CAMERA FUNCTIONS ====================
    let currentCameraStudentId = null;
    let cameraStream = null;

    function openCameraModal(studentId) {
        currentCameraStudentId = studentId;
        const modal = new bootstrap.Modal(document.getElementById('cameraModal'));
        modal.show();
        startCamera();
    }

    async function startCamera() {
        const video = document.getElementById('cameraPreview');
        const errorDiv = document.getElementById('cameraError');
        const capturedPreview = document.getElementById('capturedPreview');
        const captureBtn = document.getElementById('captureBtn');
        const retakeBtn = document.getElementById('retakeBtn');
        const useBtn = document.getElementById('useCaptureBtn');

        // Reset UI
        video.classList.remove('d-none');
        errorDiv.classList.add('d-none');
        capturedPreview.classList.add('d-none');
        captureBtn.classList.remove('d-none');
        retakeBtn.classList.add('d-none');
        useBtn.classList.add('d-none');

        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
            });
            video.srcObject = cameraStream;
        } catch (err) {
            console.error('Camera error:', err);
            video.classList.add('d-none');
            errorDiv.classList.remove('d-none');
        }
    }

    function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
    }

    // Camera modal event listeners
    document.getElementById('cameraModal')?.addEventListener('hidden.bs.modal', stopCamera);

    document.getElementById('captureBtn')?.addEventListener('click', function () {
        const video = document.getElementById('cameraPreview');
        const canvas = document.getElementById('cameraCanvas');
        const capturedImage = document.getElementById('capturedImage');
        const capturedPreview = document.getElementById('capturedPreview');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        capturedImage.src = canvas.toDataURL('image/jpeg', 0.9);
        video.classList.add('d-none');
        capturedPreview.classList.remove('d-none');
        this.classList.add('d-none');
        document.getElementById('retakeBtn').classList.remove('d-none');
        document.getElementById('useCaptureBtn').classList.remove('d-none');
    });

    document.getElementById('retakeBtn')?.addEventListener('click', startCamera);

    document.getElementById('useCaptureBtn')?.addEventListener('click', function () {
        const canvas = document.getElementById('cameraCanvas');
        canvas.toBlob(function (blob) {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const file = new File([blob], `foto_${timestamp}.jpg`, { type: 'image/jpeg' });
            addStudentFiles2(currentCameraStudentId, [file]);
            bootstrap.Modal.getInstance(document.getElementById('cameraModal')).hide();
        }, 'image/jpeg', 0.9);
    });

    // ==================== PER-STUDENT PROCESSING ====================
    async function processStudent(studentId) {
        const student = singleStudents.find(s => s.id === studentId);
        if (!student) return;

        const readiness = await checkLlmReadiness();
        if (!readiness.ready) {
            alert(readiness.message || 'Konfigurasi LLM belum siap. Hubungi admin.');
            return;
        }

        if (student.files.length === 0) {
            alert('Silakan unggah file jawaban terlebih dahulu.');
            return;
        }

        if (student.status === 'processing') {
            alert('Mahasiswa ini sedang diproses.');
            return;
        }

        // Validate at least one reference is provided
        const hasAnswerKey = singleAnswerKeyFile && singleAnswerKeyFile.files.length > 0;
        const hasQuestionDocs = singleSelectedQuestionDocs.length > 0;
        const hasAdditionalNotes = singleAdditionalNotes && singleAdditionalNotes.value.trim().length > 0;

        if (!hasAnswerKey && !hasQuestionDocs && !hasAdditionalNotes) {
            alert('Minimal satu referensi harus diisi:\n• Kunci Jawaban, atau\n• Dokumen Soal/Tugas, atau\n• Catatan Tambahan');
            return;
        }

        // Update status to processing
        student.status = 'processing';
        updateStudentStatus(studentId);

        const scoreMin = parseInt(document.getElementById('singleScoreMin').value) || 40;
        const scoreMax = parseInt(document.getElementById('singleScoreMax').value) || 100;
        const enableEvaluation = document.getElementById('singleEnableEvaluation').checked;

        const formData = new FormData();
        formData.append('csrf_token', document.querySelector('#singleUploadForm [name=csrf_token]').value);
        formData.append('score_min', scoreMin);
        formData.append('score_max', scoreMax);
        formData.append('enable_evaluation', enableEvaluation);
        formData.append('students_data', JSON.stringify([{ fileCount: student.files.length }]));

        // Add question docs
        singleSelectedQuestionDocs.forEach(file => formData.append('question_documents', file));

        // Add answer key
        if (singleAnswerKeyFile?.files.length > 0) {
            formData.append('answer_key', singleAnswerKeyFile.files[0]);
        }

        // Add notes
        if (singleAdditionalNotes?.value.trim()) {
            formData.append('additional_notes', singleAdditionalNotes.value.trim());
        }

        // Add student files
        student.files.forEach(file => formData.append('student_0_files', file));

        try {
            const response = await fetch('/api/upload-single', { method: 'POST', body: formData });
            const result = await response.json();

            if (!result.success) throw new Error(result.error);

            // Poll for result
            pollStudentResult(studentId, result.job_id);
        } catch (error) {
            student.status = 'error';
            student.result = { error: error.message };
            updateStudentStatus(studentId);
        }
    }

    async function pollStudentResult(studentId, jobId) {
        const student = singleStudents.find(s => s.id === studentId);
        if (!student) return;

        try {
            const response = await fetch(`/api/job/${jobId}`);
            const data = await response.json();

            if (data.job.status === 'completed') {
                const res = data.results[0] || {};
                student.status = 'completed';
                student.result = {
                    nim: res.nim || '[Tidak Terbaca]',
                    name: res.student_name || '[Tidak Terbaca]',
                    score: res.score,
                    evaluation: res.evaluation
                };
                updateStudentStatus(studentId);
            } else if (data.job.status === 'failed') {
                student.status = 'error';
                student.result = { error: data.job.status_message || 'Gagal memproses' };
                updateStudentStatus(studentId);
            } else {
                setTimeout(() => pollStudentResult(studentId, jobId), 2000);
            }
        } catch (error) {
            student.status = 'error';
            student.result = { error: error.message };
            updateStudentStatus(studentId);
        }
    }

    function updateStudentStatus(studentId) {
        const student = singleStudents.find(s => s.id === studentId);
        const statusDiv = document.querySelector(`.student-status[data-student-id="${studentId}"]`);
        const row = document.querySelector(`tr[data-student-id="${studentId}"]`);
        if (!student || !statusDiv || !row) return;

        // Get the action buttons (in the 4th column)
        const processBtn = row.querySelector('.btn-process-student');
        const removeBtn = row.querySelector('.btn-remove-student');

        let statusHtml = '';
        switch (student.status) {
            case 'processing':
                statusHtml = '<span class="badge bg-warning"><i class="bi bi-hourglass-split me-1"></i>Memproses...</span>';
                if (processBtn) processBtn.disabled = true;
                if (removeBtn) removeBtn.disabled = true;
                break;
            case 'completed':
                const nim = student.result?.nim || '[Tidak Terbaca]';
                const name = student.result?.name || '[Tidak Terbaca]';
                const score = student.result?.score ?? '-';
                statusHtml = `<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Selesai</span>
                        <div class="student-result-display mt-1">
                            <small><strong>NIM:</strong> ${nim}</small><br>
                            <small><strong>Nama:</strong> ${name}</small><br>
                            <small><strong>Nilai:</strong> ${score}</small>
                        </div>`;
                if (processBtn) processBtn.disabled = true;
                if (removeBtn) removeBtn.disabled = false;
                break;
            case 'error':
                statusHtml = `<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Error</span>
                        <div class="student-result-display mt-1 text-danger">
                            <small>${student.result?.error || 'Terjadi kesalahan'}</small>
                        </div>`;
                if (processBtn) {
                    processBtn.disabled = false;
                    processBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>Ulangi';
                    processBtn.classList.remove('btn-success');
                    processBtn.classList.add('btn-warning');
                }
                if (removeBtn) removeBtn.disabled = false;
                break;
            default:
                statusHtml = '<span class="badge bg-secondary">Menunggu</span>';
                if (processBtn) {
                    processBtn.disabled = false;
                    processBtn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Proses';
                    processBtn.classList.remove('btn-warning');
                    processBtn.classList.add('btn-success');
                }
                if (removeBtn) removeBtn.disabled = false;
        }
        statusDiv.innerHTML = statusHtml;
    }

    async function checkLlmReadiness() {
        try {
            const response = await fetch('/api/llm-readiness');
            if (!response.ok) {
                throw new Error('Gagal memeriksa kesiapan provider LLM');
            }
            return await response.json();
        } catch (error) {
            return {
                success: false,
                ready: false,
                provider: 'unknown',
                message: 'Tidak dapat memverifikasi konfigurasi LLM. Coba lagi atau hubungi admin.'
            };
        }
    }

    function initializeTooltips(root) {
        if (!window.bootstrap || !window.bootstrap.Tooltip) {
            return;
        }
        root.querySelectorAll('.js-tooltip[title]').forEach(el => {
            if (bootstrap.Tooltip.getInstance(el)) {
                return;
            }
            new bootstrap.Tooltip(el);
        });
    }

    function disposeTooltipsIn(root) {
        if (!window.bootstrap || !window.bootstrap.Tooltip) {
            return;
        }
        root.querySelectorAll('.js-tooltip[title]').forEach(el => {
            const instance = bootstrap.Tooltip.getInstance(el);
            if (instance) {
                instance.dispose();
            }
        });
    }
});
