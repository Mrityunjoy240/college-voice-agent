import React, { useState, useEffect } from 'react';
import {
    Box,
    Button,
    Paper,
    Typography,
    IconButton,
    Container,
    Grid,
    Card,
    CardContent,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction,
    Alert,
    CircularProgress,
    Chip,
    Divider
} from '@mui/material';
import {
    CloudUpload,
    Delete,
    Refresh,
    Description,
    TableChart,
    InsertDriveFile
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

interface FileInfo {
    filename: string;
    size: number;
    uploaded_at: string;
    processing_status?: string;
    chunks_processed?: number;
    total_chunks?: number;
}

interface Stats {
    total_files: number;
    total_size_bytes: number;
    total_chunks: number;
    groq_connected: boolean;
}

const Admin: React.FC = () => {
    const [files, setFiles] = useState<FileInfo[]>([]);
    const [stats, setStats] = useState<Stats | null>(null);
    const [uploading, setUploading] = useState(false);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [refreshInterval, setRefreshInterval] = useState<number | null>(null);
    const navigate = useNavigate();

    const [dragActive, setDragActive] = useState(false);

    useEffect(() => {
        loadFiles();
        loadStats();
        
        return () => {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        };
    }, []);

    const loadFiles = async () => {
        const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        try {
            const response = await fetch(`${API_BASE}/admin/files/`);
            if (response.ok) {
                const data = await response.json();
                setFiles(data);
                
                // Check if any files are still processing
                const hasProcessingFiles = data.some((file: FileInfo) => file.processing_status === 'processing');
                
                // Clear existing interval
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                }
                
                // Set up new interval if files are processing
                if (hasProcessingFiles) {
                    const interval = setInterval(() => {
                        loadFiles();
                    }, 3000); // Refresh every 3 seconds when processing
                    setRefreshInterval(interval);
                } else if (refreshInterval) {
                    clearInterval(refreshInterval);
                    setRefreshInterval(null);
                }
            }
        } catch (error) {
            console.error('Error loading files:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadStats = async () => {
        try {
            const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${API_BASE}/admin/stats/`);
            if (response.ok) {
                const data = await response.json();
                setStats(data);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    };

    const processFile = async (file: File) => {
        // Validate file type
        const validExtensions = ['.pdf', '.xlsx', '.xls', '.csv', '.txt'];
        const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        
        if (!validExtensions.includes(fileExt)) {
            setMessage({
                type: 'error',
                text: `Invalid file type. Supported: ${validExtensions.join(', ')}`
            });
            return;
        }

        setUploading(true);
        setMessage(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/admin/files/', {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                setMessage({
                    type: 'success',
                    text: `✅ ${data.filename} uploaded successfully! Processing...`
                });
                
                // Refresh lists after a delay to allow processing
                setTimeout(() => {
                    loadFiles();
                    loadStats();
                }, 2000);
            } else {
                const error = await response.json();
                setMessage({
                    type: 'error',
                    text: `❌ Upload failed: ${error.detail}`
                });
            }
        } catch (error) {
            setMessage({
                type: 'error',
                text: '❌ Network error. Please check if backend is running.'
            });
        } finally {
            setUploading(false);
        }
    };

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            processFile(file);
        }
        // Clear file input
        event.target.value = '';
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            processFile(e.dataTransfer.files[0]);
        }
    };

    const handleDelete = async (filename: string) => {
        if (!confirm(`Delete ${filename}?`)) return;

        try {
            const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${API_BASE}/admin/files/${filename}`, {
                method: 'DELETE',
            });

            if (response.ok) {
                setMessage({
                    type: 'success',
                    text: `✅ ${filename} deleted successfully!`
                });
                loadFiles();
                loadStats();
            } else {
                setMessage({
                    type: 'error',
                    text: '❌ Failed to delete file'
                });
            }
        } catch (error) {
            setMessage({
                type: 'error',
                text: '❌ Network error'
            });
        }
    };

    const handleRebuild = async () => {
        if (!confirm('Rebuild all embeddings? This will take a few minutes.')) return;

        try {
            const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${API_BASE}/admin/rebuild-embeddings/`, {
                method: 'POST',
            });

            if (response.ok) {
                setMessage({
                    type: 'success',
                    text: '✅ Rebuilding embeddings in background...'
                });
                
                setTimeout(() => {
                    loadStats();
                }, 5000);
            }
        } catch (error) {
            setMessage({
                type: 'error',
                text: '❌ Failed to rebuild embeddings'
            });
        }
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    const getFileIcon = (filename: string) => {
        const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();
        if (ext === '.pdf') return <Description color="error" />;
        if (['.xlsx', '.xls', '.csv'].includes(ext)) return <TableChart color="success" />;
        return <InsertDriveFile color="primary" />;
    };

    return (
        <Container maxWidth="lg">
            <Box sx={{ py: 4 }}>
                {/* Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
                    <Typography variant="h4" gutterBottom>
                        📊 Admin Dashboard
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2 }}>
                        <Button 
                            startIcon={<Refresh />} 
                            onClick={() => { loadStats(); loadFiles(); }}
                            sx={{ mr: 1 }}
                        >
                            Refresh
                        </Button>
                        <Button variant="outlined" onClick={() => navigate('/')}>
                            ← Back to Chat
                        </Button>
                    </Box>
                </Box>

                {/* Message Alert */}
                {message && (
                    <Alert 
                        severity={message.type} 
                        sx={{ mb: 3 }}
                        onClose={() => setMessage(null)}
                    >
                        {message.text}
                    </Alert>
                )}

                {/* Stats Cards */}
                <Grid container spacing={3} sx={{ mb: 4 }}>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="text.secondary" gutterBottom>
                                    Total Files
                                </Typography>
                                <Typography variant="h4">
                                    {stats?.total_files || 0}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="text.secondary" gutterBottom>
                                    Storage Used
                                </Typography>
                                <Typography variant="h4">
                                    {stats ? formatFileSize(stats.total_size_bytes) : '0 B'}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="text.secondary" gutterBottom>
                                    Document Chunks
                                </Typography>
                                <Typography variant="h4">
                                    {stats?.total_chunks || 0}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="text.secondary" gutterBottom>
                                    AI Status
                                </Typography>
                                <Chip 
                                    label={stats?.groq_connected ? '✓ Connected' : '✗ Disconnected'}
                                    color={stats?.groq_connected ? 'success' : 'error'}
                                    sx={{ mt: 1 }}
                                />
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>

                {/* Upload Section */}
                <Paper sx={{ p: 3, mb: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        📤 Upload Documents
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Supported formats: PDF, Excel (.xlsx, .xls), CSV, TXT
                    </Typography>
                    
                    <Box
                        sx={{
                            border: '2px dashed',
                            borderColor: dragActive ? 'primary.main' : 'primary.light',
                            borderRadius: 2,
                            p: 4,
                            textAlign: 'center',
                            bgcolor: dragActive ? 'primary.50' : 'background.paper',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease-in-out',
                            '&:hover': {
                                bgcolor: 'primary.50',
                                borderColor: 'primary.main',
                            }
                        }}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        onClick={() => document.getElementById('file-upload')?.click()}
                    >
                        {uploading ? (
                            <CircularProgress />
                        ) : (
                            <>
                                <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                                <Typography variant="h6" gutterBottom>
                                    Click to Upload or Drag & Drop
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Maximum file size: 50MB
                                </Typography>
                            </>
                        )}
                    </Box>
                    
                    <input
                        id="file-upload"
                        type="file"
                        accept=".pdf,.xlsx,.xls,.csv,.txt"
                        onChange={handleFileUpload}
                        style={{ display: 'none' }}
                    />
                </Paper>

                {/* Files List */}
                <Paper sx={{ p: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6">
                            📁 Uploaded Files ({files.length})
                        </Typography>
                        <Box>
                            <IconButton onClick={loadFiles} title="Refresh">
                                <Refresh />
                            </IconButton>
                            <Button
                                variant="outlined"
                                onClick={handleRebuild}
                                size="small"
                                sx={{ ml: 1 }}
                            >
                                🔄 Rebuild Embeddings
                            </Button>
                        </Box>
                    </Box>

                    <Divider sx={{ mb: 2 }} />

                    {loading ? (
                        <Box sx={{ textAlign: 'center', py: 4 }}>
                            <CircularProgress />
                        </Box>
                    ) : files.length === 0 ? (
                        <Box sx={{ textAlign: 'center', py: 4 }}>
                            <Typography color="text.secondary">
                                No files uploaded yet. Upload your first document above!
                            </Typography>
                        </Box>
                    ) : (
                        <List>
                            {files.map((file, index) => (
                                <ListItem
                                    key={index}
                                    sx={{
                                        border: '1px solid',
                                        borderColor: 'divider',
                                        borderRadius: 1,
                                        mb: 1,
                                    }}
                                >
                                    <Box sx={{ mr: 2 }}>
                                        {getFileIcon(file.filename)}
                                    </Box>
                                    <ListItemText
                                        primary={
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <span>{file.filename}</span>
                                                {file.processing_status === 'processing' && (
                                                    <CircularProgress size={16} />
                                                )}
                                                {file.processing_status === 'completed' && (
                                                    <Chip label="Completed" size="small" color="success" />
                                                )}
                                                {file.processing_status === 'failed' && (
                                                    <Chip label="Failed" size="small" color="error" />
                                                )}
                                                {file.processing_status === 'uploaded' && (
                                                    <Chip label="Uploaded" size="small" color="warning" />
                                                )}
                                            </Box>
                                        }
                                        secondary={
                                            <Box>
                                                <div>Size: {formatFileSize(file.size)} • Uploaded: {new Date(parseFloat(file.uploaded_at) * 1000).toLocaleString()}</div>
                                                {file.processing_status === 'processing' && file.total_chunks && file.total_chunks > 0 && (
                                                    <div>Processing: {file.chunks_processed || 0}/{file.total_chunks} chunks</div>
                                                )}
                                            </Box>
                                        }
                                    />
                                    <ListItemSecondaryAction>
                                        <IconButton
                                            edge="end"
                                            onClick={() => handleDelete(file.filename)}
                                            color="error"
                                        >
                                            <Delete />
                                        </IconButton>
                                    </ListItemSecondaryAction>
                                </ListItem>
                            ))}
                        </List>
                    )}
                </Paper>

                {/* Info Box */}
                <Alert severity="info" sx={{ mt: 3 }}>
                    <strong>How it works:</strong>
                    <br />
                    1. Upload your college documents (PDF, Excel, CSV, or Text files)
                    <br />
                    2. Files are automatically processed and indexed
                    <br />
                    3. Ask questions in the Voice Chat and get accurate answers from your documents
                    <br />
                    4. Use "Rebuild Embeddings" if you need to reprocess all files
                </Alert>
            </Box>
        </Container>
    );
};

export default Admin;
