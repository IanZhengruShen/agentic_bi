'use client';

/**
 * Custom Template Creator Component
 *
 * Allows users to create custom Plotly templates by configuring:
 * - Color palette
 * - Fonts
 * - Backgrounds
 * - Hover behavior
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import type {
  ChartTemplateConfig,
  CustomTemplateDefinition,
  SavedTemplate,
} from '@/types/chartPreferences.types';
import { createCustomTemplateConfig, saveCustomTemplate, updateCustomTemplate } from '@/services/chartPreferences.service';

interface CustomTemplateCreatorProps {
  onTemplateCreated: (template: ChartTemplateConfig) => void;
  editingTemplate?: SavedTemplate | null;
  onEditComplete?: () => void;
}

export function CustomTemplateCreator({ onTemplateCreated, editingTemplate, onEditComplete }: CustomTemplateCreatorProps) {
  // Color palette (4 main colors)
  const [colors, setColors] = useState<string[]>([
    '#3b82f6', // blue
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
  ]);

  // Font settings
  const [fontFamily, setFontFamily] = useState('Arial, sans-serif');
  const [fontSize, setFontSize] = useState(12);

  // Background colors
  const [plotBgColor, setPlotBgColor] = useState('#ffffff');
  const [paperBgColor, setPaperBgColor] = useState('#ffffff');

  // Hover mode
  const [hoverMode, setHoverMode] = useState('x unified');

  // Logo settings
  const [logoUrl, setLogoUrl] = useState('');
  const [logoX, setLogoX] = useState(1);
  const [logoY, setLogoY] = useState(1.05);
  const [logoSizeX, setLogoSizeX] = useState(0.15);
  const [logoSizeY, setLogoSizeY] = useState(0.15);

  // Load editing template values
  useEffect(() => {
    if (editingTemplate?.template_definition?.layout) {
      const layout = editingTemplate.template_definition.layout;

      if (layout.colorway) {
        setColors(layout.colorway.slice(0, 4));
      }
      if (layout.font) {
        setFontFamily(layout.font.family || 'Arial, sans-serif');
        setFontSize(layout.font.size || 12);
      }
      if (layout.plot_bgcolor) {
        setPlotBgColor(layout.plot_bgcolor);
      }
      if (layout.paper_bgcolor) {
        setPaperBgColor(layout.paper_bgcolor);
      }
      if (layout.hovermode) {
        setHoverMode(layout.hovermode);
      }
      if (layout.logo_url) {
        setLogoUrl(layout.logo_url);
      }
      if (layout.logo_position) {
        setLogoX(layout.logo_position.x || 1);
        setLogoY(layout.logo_position.y || 1.05);
        setLogoSizeX(layout.logo_position.sizex || 0.15);
        setLogoSizeY(layout.logo_position.sizey || 0.15);
      }
    }
  }, [editingTemplate]);

  const handleColorChange = (index: number, value: string) => {
    const newColors = [...colors];
    newColors[index] = value;
    setColors(newColors);
  };

  const handleApplyTemplate = () => {
    const customDefinition: CustomTemplateDefinition = {
      layout: {
        font: {
          family: fontFamily,
          size: fontSize,
          color: '#333333',
        },
        colorway: colors,
        plot_bgcolor: plotBgColor,
        paper_bgcolor: paperBgColor,
        hovermode: hoverMode,
        logo_url: logoUrl || undefined,
        logo_position: logoUrl ? {
          x: logoX,
          y: logoY,
          sizex: logoSizeX,
          sizey: logoSizeY,
          xanchor: 'right',
          yanchor: 'bottom',
        } : undefined,
      },
    };

    const template = createCustomTemplateConfig(customDefinition);
    onTemplateCreated(template);
    toast.success('Custom template applied to preview');
  };

  const handleSaveAsTemplate = async () => {
    const isEditing = !!editingTemplate;
    const name = prompt(
      isEditing ? 'Update template name:' : 'Enter a name for this template:',
      isEditing ? editingTemplate.name : ''
    );
    if (!name) return;

    const description = prompt(
      'Enter a description (optional):',
      isEditing ? (editingTemplate.description || '') : ''
    );

    try {
      const customDefinition: CustomTemplateDefinition = {
        layout: {
          font: {
            family: fontFamily,
            size: fontSize,
            color: '#333333',
          },
          colorway: colors,
          plot_bgcolor: plotBgColor,
          paper_bgcolor: paperBgColor,
          hovermode: hoverMode,
          logo_url: logoUrl || undefined,
          logo_position: logoUrl ? {
            x: logoX,
            y: logoY,
            sizex: logoSizeX,
            sizey: logoSizeY,
            xanchor: 'right',
            yanchor: 'bottom',
          } : undefined,
        },
      };

      if (isEditing) {
        await updateCustomTemplate(editingTemplate.id, {
          name,
          description: description || undefined,
          template_definition: customDefinition,
        });
        toast.success('Template updated successfully');
        onEditComplete?.();
      } else {
        await saveCustomTemplate({
          name,
          description: description || undefined,
          template_definition: customDefinition,
        });
        toast.success('Template saved successfully');
      }
    } catch (error) {
      console.error('Failed to save template:', error);
      toast.error(`Failed to ${isEditing ? 'update' : 'save'} template`);
    }
  };

  return (
    <div className="space-y-6">
      {editingTemplate && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-blue-900">
              Editing: {editingTemplate.name}
            </div>
            <div className="text-xs text-blue-700">
              Make changes and click "Update Template" to save
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={onEditComplete}
            className="text-xs"
          >
            Cancel Edit
          </Button>
        </div>
      )}
      <div className="text-sm text-gray-600">
        {editingTemplate
          ? 'Adjust the template settings below and save your changes.'
          : 'Create a custom chart style by adjusting colors, fonts, and layout settings.'}
      </div>

      {/* Color Palette */}
      <Card className="p-4">
        <Label className="text-base font-semibold mb-4 block">Color Palette</Label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {colors.map((color, index) => (
            <div key={index} className="space-y-2">
              <Label className="text-sm">Color {index + 1}</Label>
              <div className="flex gap-2">
                <Input
                  type="color"
                  value={color}
                  onChange={(e) => handleColorChange(index, e.target.value)}
                  className="h-10 w-16 cursor-pointer"
                />
                <Input
                  type="text"
                  value={color}
                  onChange={(e) => handleColorChange(index, e.target.value)}
                  className="flex-1 font-mono text-sm"
                />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Font Settings */}
      <Card className="p-4">
        <Label className="text-base font-semibold mb-4 block">Font Settings</Label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label className="text-sm">Font Family</Label>
            <Select value={fontFamily} onValueChange={setFontFamily}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Arial, sans-serif">Arial</SelectItem>
                <SelectItem value="Helvetica, sans-serif">Helvetica</SelectItem>
                <SelectItem value="'Times New Roman', serif">Times New Roman</SelectItem>
                <SelectItem value="'Courier New', monospace">Courier New</SelectItem>
                <SelectItem value="Georgia, serif">Georgia</SelectItem>
                <SelectItem value="'Inter', sans-serif">Inter</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-sm">Font Size: {fontSize}px</Label>
            <Input
              type="range"
              min="10"
              max="18"
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value))}
              className="cursor-pointer"
            />
          </div>
        </div>
      </Card>

      {/* Background Colors */}
      <Card className="p-4">
        <Label className="text-base font-semibold mb-4 block">Background Colors</Label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label className="text-sm">Plot Background</Label>
            <div className="flex gap-2">
              <Input
                type="color"
                value={plotBgColor}
                onChange={(e) => setPlotBgColor(e.target.value)}
                className="h-10 w-16 cursor-pointer"
              />
              <Input
                type="text"
                value={plotBgColor}
                onChange={(e) => setPlotBgColor(e.target.value)}
                className="flex-1 font-mono text-sm"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-sm">Paper Background</Label>
            <div className="flex gap-2">
              <Input
                type="color"
                value={paperBgColor}
                onChange={(e) => setPaperBgColor(e.target.value)}
                className="h-10 w-16 cursor-pointer"
              />
              <Input
                type="text"
                value={paperBgColor}
                onChange={(e) => setPaperBgColor(e.target.value)}
                className="flex-1 font-mono text-sm"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Hover Mode */}
      <Card className="p-4">
        <Label className="text-base font-semibold mb-4 block">Hover Behavior</Label>
        <Select value={hoverMode} onValueChange={setHoverMode}>
          <SelectTrigger className="w-full md:w-64">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="x">X - Show all points at same X</SelectItem>
            <SelectItem value="y">Y - Show all points at same Y</SelectItem>
            <SelectItem value="x unified">X Unified - Unified hover box</SelectItem>
            <SelectItem value="closest">Closest - Show nearest point</SelectItem>
            <SelectItem value="false">Disabled - No hover</SelectItem>
          </SelectContent>
        </Select>
      </Card>

      {/* Company Logo */}
      <Card className="p-4">
        <Label className="text-base font-semibold mb-4 block">Company Logo (Optional)</Label>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label className="text-sm">Logo URL</Label>
            <Input
              type="text"
              placeholder="https://example.com/logo.png or data:image/png;base64,..."
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              className="font-mono text-sm"
            />
            <p className="text-xs text-gray-500">
              Enter a URL to your logo image or a base64 data URI
            </p>
          </div>

          {logoUrl && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm">Position X: {logoX.toFixed(2)}</Label>
                  <Input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={logoX}
                    onChange={(e) => setLogoX(Number(e.target.value))}
                    className="cursor-pointer"
                  />
                  <p className="text-xs text-gray-500">0 = left, 1 = right</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm">Position Y: {logoY.toFixed(2)}</Label>
                  <Input
                    type="range"
                    min="0"
                    max="1.2"
                    step="0.05"
                    value={logoY}
                    onChange={(e) => setLogoY(Number(e.target.value))}
                    className="cursor-pointer"
                  />
                  <p className="text-xs text-gray-500">0 = bottom, 1 = top, &gt;1 = above</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm">Width: {logoSizeX.toFixed(2)}</Label>
                  <Input
                    type="range"
                    min="0.05"
                    max="0.5"
                    step="0.01"
                    value={logoSizeX}
                    onChange={(e) => setLogoSizeX(Number(e.target.value))}
                    className="cursor-pointer"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm">Height: {logoSizeY.toFixed(2)}</Label>
                  <Input
                    type="range"
                    min="0.05"
                    max="0.5"
                    step="0.01"
                    value={logoSizeY}
                    onChange={(e) => setLogoSizeY(Number(e.target.value))}
                    className="cursor-pointer"
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          onClick={handleApplyTemplate}
          className="bg-blue-600 hover:bg-blue-700"
        >
          Apply to Preview
        </Button>
        <Button
          onClick={handleSaveAsTemplate}
          variant="outline"
        >
          {editingTemplate ? 'Update Template' : 'Save as Template'}
        </Button>
      </div>
    </div>
  );
}
