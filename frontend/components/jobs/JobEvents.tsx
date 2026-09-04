'use client';

import React, { useRef, useEffect } from 'react';
import { formatDate } from '@/lib/utils';
import type { JobEvent } from '@/types/job';

interface JobEventsProps {
  events: JobEvent[];
  loading?: boolean;
  autoScroll?: boolean;
  maxHeight?: number;
}

const levelColor: Record<string, string> = {
  debug: 'rgba(200,220,255,0.35)',
  info: '#00d4ff',
  warning: '#ffab00',
  error: '#ff4d6d',
};

const levelBg: Record<string, string> = {
  debug: 'rgba(200,220,255,0.05)',
  info: 'rgba(0,212,255,0.04)',
  warning: 'rgba(255,171,0,0.06)',
  error: 'rgba(255,61,113,0.08)',
};

export const JobEvents: React.FC<JobEventsProps> = ({
  events,
  loading = false,
  autoScroll = true,
  maxHeight = 480,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, autoScroll]);

  return (
    <div
      style={{
        background: 'rgba(2,11,24,0.85)',
        border: '1px solid rgba(0,212,255,0.12)',
        borderRadius: '10px',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid rgba(0,212,255,0.08)',
          background: 'rgba(7,20,40,0.5)',
        }}
      >
        <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'rgba(200,220,255,0.6)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
          Event Log
        </span>
        <span style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.35)' }}>
          {events.length} events
        </span>
      </div>

      {/* Events list */}
      <div
        style={{
          maxHeight,
          overflowY: 'auto',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.8rem',
        }}
      >
        {loading && events.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'rgba(200,220,255,0.3)' }}>
            Waiting for events...
          </div>
        ) : events.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'rgba(200,220,255,0.3)' }}>
            No events yet.
          </div>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              style={{
                display: 'flex',
                gap: '12px',
                padding: '8px 16px',
                borderBottom: '1px solid rgba(0,212,255,0.04)',
                background: levelBg[event.level] ?? 'transparent',
                alignItems: 'flex-start',
              }}
            >
              {/* Timestamp */}
              <span style={{ fontSize: '0.7rem', color: 'rgba(200,220,255,0.25)', whiteSpace: 'nowrap', paddingTop: '1px', minWidth: '80px' }}>
                {new Date(event.timestamp).toLocaleTimeString('en-US', { hour12: false })}
              </span>

              {/* Level */}
              <span
                style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  color: levelColor[event.level] ?? 'rgba(200,220,255,0.4)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  minWidth: '50px',
                  paddingTop: '1px',
                }}
              >
                {event.level}
              </span>

              {/* Message */}
              <span
                style={{
                  flex: 1,
                  color: event.level === 'error' ? '#ff8080' : event.level === 'warning' ? '#ffcc55' : 'rgba(200,220,255,0.8)',
                  lineHeight: 1.5,
                  wordBreak: 'break-word',
                }}
              >
                {event.message}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default JobEvents;
