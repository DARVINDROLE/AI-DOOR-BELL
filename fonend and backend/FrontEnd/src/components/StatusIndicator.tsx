import { cn } from '@/lib/utils';
import { Mic, Loader2, Volume2, Circle } from 'lucide-react';

type Status = 'idle' | 'listening' | 'processing' | 'speaking';

interface StatusIndicatorProps {
  status: Status;
  message?: string;
  audioLevel?: number;
}

const statusConfig = {
  idle: {
    icon: Circle,
    label: 'Ready',
    color: 'text-muted-foreground',
    bgColor: 'bg-muted-foreground/20',
  },
  listening: {
    icon: Mic,
    label: 'Listening...',
    color: 'text-primary',
    bgColor: 'bg-primary/20',
  },
  processing: {
    icon: Loader2,
    label: 'Processing...',
    color: 'text-accent',
    bgColor: 'bg-accent/20',
  },
  speaking: {
    icon: Volume2,
    label: 'Speaking...',
    color: 'text-success',
    bgColor: 'bg-success/20',
  },
};

export function StatusIndicator({ status, message, audioLevel = 0 }: StatusIndicatorProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className="flex flex-col items-center gap-4 slide-up">
      {/* Status badge */}
      <div 
        className={cn(
          "flex items-center gap-3 px-6 py-3 rounded-full transition-all duration-300",
          config.bgColor
        )}
      >
        {/* Animated dot */}
        <div className={cn("status-dot", status)} />
        
        {/* Icon */}
        <Icon 
          className={cn(
            "w-5 h-5 transition-all duration-300",
            config.color,
            status === 'processing' && "animate-spin",
            status === 'listening' && "animate-pulse"
          )} 
        />
        
        {/* Label */}
        <span className={cn("font-medium", config.color)}>
          {message || config.label}
        </span>
      </div>

      {/* Audio level visualizer for listening state */}
      {status === 'listening' && (
        <div className="flex items-center gap-1 h-8">
          {[...Array(12)].map((_, i) => {
            const height = Math.max(4, Math.min(32, audioLevel * 40 + Math.random() * 8));
            return (
              <div
                key={i}
                className="w-1 bg-primary rounded-full transition-all duration-75"
                style={{ 
                  height: `${height}px`,
                  opacity: 0.4 + (audioLevel * 0.6),
                }}
              />
            );
          })}
        </div>
      )}

      {/* Speaking wave animation */}
      {status === 'speaking' && (
        <div className="flex items-center gap-1 h-8">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="w-1.5 bg-success rounded-full animate-pulse"
              style={{ 
                height: `${12 + Math.sin(i * 0.8) * 8}px`,
                animationDelay: `${i * 0.1}s`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
