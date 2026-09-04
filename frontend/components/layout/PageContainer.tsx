'use client';

import React from 'react';

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  maxWidth?: string | number;
}

export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  className,
  maxWidth = 1400,
}) => {
  return (
    <main
      className={className}
      style={{
        padding: '28px 32px',
        maxWidth: typeof maxWidth === 'number' ? `${maxWidth}px` : maxWidth,
        width: '100%',
        flex: 1,
        animation: 'fadeIn 0.25s ease',
      }}
    >
      {children}
    </main>
  );
};

export default PageContainer;
