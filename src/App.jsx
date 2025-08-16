import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { 
  Play, Pause, Settings, BarChart3, Video, Clock, AlertCircle, 
  CheckCircle, XCircle, FileText, Activity, Download 
} from 'lucide-react';
import './App.css';

// Components
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Alert, AlertDescription } from './components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import VideoPreview from './components/VideoPreview';

// Main Dashboard Component
function Dashboard() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [videos, setVideos] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [schedulerRunning, setSchedulerRunning] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch system status
  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('/api/automation/status');
      const data = await response.json();
      if (data.success) {
        setSystemStatus(data);
        setSchedulerRunning(data.system_status.scheduler_running);
      }
    } catch (error) {
      console.error('Error fetching system status:', error);
    }
  };

  // Fetch videos
  const fetchVideos = async () => {
    try {
      const response = await fetch('/api/automation/videos?per_page=10');
      const data = await response.json();
      if (data.success) {
        setVideos(data.videos);
      }
    } catch (error) {
      console.error('Error fetching videos:', error);
    }
  };

  // Fetch logs
  const fetchLogs = async (logType = 'all') => {
    try {
      const response = await fetch(`/api/automation/logs?type=${logType}&limit=50`);
      const data = await response.json();
      if (data.success) {
        setLogs(data.logs);
      }
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  };

  // Start scheduler
  const startScheduler = async () => {
    try {
      const response = await fetch('/api/automation/scheduler/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (data.success) {
        setSchedulerRunning(true);
        fetchSystemStatus();
      }
    } catch (error) {
      console.error('Error starting scheduler:', error);
    }
  };

  // Stop scheduler
  const stopScheduler = async () => {
    try {
      const response = await fetch('/api/automation/scheduler/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (data.success) {
        setSchedulerRunning(false);
        fetchSystemStatus();
      }
    } catch (error) {
      console.error('Error stopping scheduler:', error);
    }
  };

  // Generate video manually
  const generateVideo = async () => {
    try {
      const response = await fetch('/api/automation/generate-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (data.success) {
        // Refresh data
        setTimeout(() => {
          fetchSystemStatus();
          fetchVideos();
        }, 1000);
      }
    } catch (error) {
      console.error('Error generating video:', error);
    }
  };

  // Load data on component mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchSystemStatus(), fetchVideos(), fetchLogs()]);
      setLoading(false);
    };
    
    loadData();
    
    // Set up auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchSystemStatus();
      fetchVideos();
      if (activeTab === 'logs') {
        fetchLogs();
      }
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  // Refresh logs when tab changes
  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
    }
  }, [activeTab]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      processing: 'bg-blue-100 text-blue-800',
      pending: 'bg-yellow-100 text-yellow-800'
    };
    
    return (
      <Badge className={variants[status] || 'bg-gray-100 text-gray-800'}>
        {status}
      </Badge>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Video className="h-8 w-8 text-blue-600 mr-3" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">No Spin News</h1>
                <p className="text-sm text-gray-500">YouTube Automation Dashboard</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <Button
                onClick={generateVideo}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Play className="h-4 w-4 mr-2" />
                Generate Video Now
              </Button>
              
              {schedulerRunning ? (
                <Button
                  onClick={stopScheduler}
                  variant="outline"
                  className="border-red-300 text-red-700 hover:bg-red-50"
                >
                  <Pause className="h-4 w-4 mr-2" />
                  Stop Scheduler
                </Button>
              ) : (
                <Button
                  onClick={startScheduler}
                  variant="outline"
                  className="border-green-300 text-green-700 hover:bg-green-50"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Start Scheduler
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Scheduler Status</CardTitle>
              <Settings className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {schedulerRunning ? (
                  <span className="text-green-600">Running</span>
                ) : (
                  <span className="text-red-600">Stopped</span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {schedulerRunning ? 'Generating videos every hour' : 'Automation paused'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Videos</CardTitle>
              <Video className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {systemStatus?.system_status?.total_videos || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                All time generated
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {Math.round(systemStatus?.system_status?.success_rate || 0)}%
              </div>
              <p className="text-xs text-muted-foreground">
                {systemStatus?.system_status?.successful_videos || 0} successful
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Failed Videos</CardTitle>
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {systemStatus?.system_status?.failed_videos || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                Need attention
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Scheduler Status Alert */}
        {schedulerRunning && (
          <Alert className="mb-6 border-green-200 bg-green-50">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              Automation is running! Videos are being generated every hour and uploaded to YouTube automatically.
            </AlertDescription>
          </Alert>
        )}

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview" className="flex items-center space-x-2">
              <Video className="h-4 w-4" />
              <span>Videos</span>
            </TabsTrigger>
            <TabsTrigger value="logs" className="flex items-center space-x-2">
              <FileText className="h-4 w-4" />
              <span>Logs</span>
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center space-x-2">
              <Activity className="h-4 w-4" />
              <span>Analytics</span>
            </TabsTrigger>
          </TabsList>

          {/* Videos Tab */}
          <TabsContent value="overview" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Recent Videos</CardTitle>
                <CardDescription>
                  Latest generated videos with preview and download options
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {videos.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">
                      No videos generated yet. Click "Generate Video Now" to create your first video!
                    </p>
                  ) : (
                    videos.map((video) => (
                      <VideoPreview key={video.id} video={video} />
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>System Logs</CardTitle>
                    <CardDescription>
                      Real-time logging for debugging and monitoring
                    </CardDescription>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      onClick={() => fetchLogs('all')}
                      variant="outline"
                      size="sm"
                    >
                      All Logs
                    </Button>
                    <Button
                      onClick={() => fetchLogs('api')}
                      variant="outline"
                      size="sm"
                    >
                      API Calls
                    </Button>
                    <Button
                      onClick={() => fetchLogs('errors')}
                      variant="outline"
                      size="sm"
                    >
                      Errors
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
                  {logs.length === 0 ? (
                    <p className="text-gray-500">No logs available</p>
                  ) : (
                    logs.map((log, index) => (
                      <div key={index} className="mb-1 break-all">
                        {log}
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>API Usage Today</CardTitle>
                  <CardDescription>
                    API calls and estimated costs
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {systemStatus?.api_usage_today?.length === 0 ? (
                      <p className="text-gray-500">No API usage data for today</p>
                    ) : (
                      systemStatus?.api_usage_today?.map((usage, index) => (
                        <div key={index} className="flex items-center justify-between p-3 border rounded">
                          <div>
                            <p className="font-medium">{usage.service}</p>
                            <p className="text-sm text-gray-500">{usage.endpoint}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium">{usage.requests_count} calls</p>
                            {usage.estimated_cost && (
                              <p className="text-sm text-gray-500">${usage.estimated_cost.toFixed(4)}</p>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>System Components</CardTitle>
                  <CardDescription>
                    Health status of system components
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {systemStatus?.system_components?.length === 0 ? (
                      <p className="text-gray-500">No component status data</p>
                    ) : (
                      systemStatus?.system_components?.map((component, index) => (
                        <div key={index} className="flex items-center justify-between p-3 border rounded">
                          <div>
                            <p className="font-medium">{component.component}</p>
                            <p className="text-sm text-gray-500">
                              Last check: {new Date(component.last_check_at).toLocaleString()}
                            </p>
                          </div>
                          <div className="text-right">
                            <Badge className={
                              component.status === 'healthy' ? 'bg-green-100 text-green-800' :
                              component.status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }>
                              {component.status}
                            </Badge>
                            {component.response_time_ms && (
                              <p className="text-sm text-gray-500 mt-1">
                                {component.response_time_ms}ms
                              </p>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

// Main App Component
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;

