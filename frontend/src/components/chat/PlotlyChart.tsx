'use client';

import dynamic from 'next/dynamic';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';

// Dynamically import Plot to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface PlotlyChartProps {
  figure: any;
  title?: string;
}

export default function PlotlyChart({ figure, title }: PlotlyChartProps) {
  if (!figure || !figure.data) {
    return null;
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center">
          <BarChart3 size={18} className="mr-2" />
          {title || figure.layout?.title?.text || 'Visualization'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full">
          <Plot
            data={figure.data}
            layout={{
              ...figure.layout,
              autosize: true,
              responsive: true,
              margin: { l: 50, r: 50, t: 50, b: 50 },
            }}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            }}
            style={{ width: '100%', height: '400px' }}
            useResizeHandler={true}
          />
        </div>
      </CardContent>
    </Card>
  );
}
