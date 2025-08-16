import React, { useState, useRef } from 'react';
import { Play, Pause, Download, ExternalLink, Volume2, VolumeX, Maximize2 } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';

const VideoPreview = ({ video }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const videoRef = useRef(null);

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleMuteToggle = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (e) => {
    if (videoRef.current) {
      const rect = e.currentTarget.getBoundingClientRect();
      const pos = (e.clientX - rect.left) / rect.width;
      videoRef.current.currentTime = pos * duration;
    }
  };

  const handleFullscreen = () => {
    if (videoRef.current) {
      if (videoRef.current.requestFullscreen) {
        videoRef.current.requestFullscreen();
      }
    }
  };

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleDownload = () => {
    if (video.download_url) {
      window.open(video.download_url, '_blank');
    }
  };

  const handleYouTubeOpen = () => {
    if (video.youtube_url) {
      window.open(video.youtube_url, '_blank');
    }
  };

  if (!video.has_local_file || !video.preview_url) {
    return (
      <Card className="w-full">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-lg mb-2">
                {video.title || `Video #${video.id}`}
              </h3>
              <p className="text-sm text-gray-500 mb-2">
                Created: {new Date(video.created_at).toLocaleString()}
              </p>
              <div className="flex items-center space-x-2">
                <Badge className={
                  video.status === 'completed' ? 'bg-green-100 text-green-800' :
                  video.status === 'failed' ? 'bg-red-100 text-red-800' :
                  video.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                  'bg-yellow-100 text-yellow-800'
                }>
                  {video.status}
                </Badge>
                {video.duration_seconds && (
                  <span className="text-sm text-gray-500">
                    {Math.round(video.duration_seconds)}s
                  </span>
                )}
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              {video.youtube_url && (
                <Button
                  onClick={handleYouTubeOpen}
                  variant="outline"
                  size="sm"
                  className="text-red-600 border-red-300 hover:bg-red-50"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  YouTube
                </Button>
              )}
              <div className="text-sm text-gray-500">
                {video.status === 'completed' ? 'Video file not available' : 'Processing...'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* Video Header */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-lg mb-1">
                {video.title || `Video #${video.id}`}
              </h3>
              <p className="text-sm text-gray-500">
                Created: {new Date(video.created_at).toLocaleString()}
              </p>
            </div>
            
            <div className="flex items-center space-x-2">
              <Badge className="bg-green-100 text-green-800">
                {video.status}
              </Badge>
              {video.file_size_mb && (
                <span className="text-sm text-gray-500">
                  {video.file_size_mb.toFixed(1)} MB
                </span>
              )}
            </div>
          </div>

          {/* Video Player */}
          <div className="relative bg-black rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              className="w-full h-auto max-h-96"
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              preload="metadata"
            >
              <source src={video.preview_url} type="video/mp4" />
              Your browser does not support the video tag.
            </video>

            {/* Video Controls Overlay */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4">
              {/* Progress Bar */}
              <div 
                className="w-full h-1 bg-white/30 rounded-full mb-3 cursor-pointer"
                onClick={handleSeek}
              >
                <div 
                  className="h-full bg-white rounded-full transition-all duration-150"
                  style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
                />
              </div>

              {/* Control Buttons */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <button
                    onClick={handlePlayPause}
                    className="text-white hover:text-gray-300 transition-colors"
                  >
                    {isPlaying ? (
                      <Pause className="h-6 w-6" />
                    ) : (
                      <Play className="h-6 w-6" />
                    )}
                  </button>
                  
                  <button
                    onClick={handleMuteToggle}
                    className="text-white hover:text-gray-300 transition-colors"
                  >
                    {isMuted ? (
                      <VolumeX className="h-5 w-5" />
                    ) : (
                      <Volume2 className="h-5 w-5" />
                    )}
                  </button>
                  
                  <span className="text-white text-sm">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleFullscreen}
                    className="text-white hover:text-gray-300 transition-colors"
                  >
                    <Maximize2 className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center space-x-2">
              {video.youtube_url && (
                <Button
                  onClick={handleYouTubeOpen}
                  variant="outline"
                  size="sm"
                  className="text-red-600 border-red-300 hover:bg-red-50"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View on YouTube
                </Button>
              )}
              
              <Button
                onClick={handleDownload}
                variant="outline"
                size="sm"
                className="text-blue-600 border-blue-300 hover:bg-blue-50"
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>

            <div className="text-sm text-gray-500">
              {video.duration_seconds && `${Math.round(video.duration_seconds)}s`}
            </div>
          </div>

          {/* Video Description */}
          {video.description && (
            <div className="pt-2 border-t">
              <p className="text-sm text-gray-600 line-clamp-3">
                {video.description}
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default VideoPreview;

