'use client';

/**
 * Profile Settings Component
 *
 * Allows users to manage their profile information:
 * - Name, email, avatar
 * - Bio, job title
 * - Timezone, language preferences
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { User, Mail, Briefcase, Globe, Clock } from 'lucide-react';

export function ProfileSettings() {
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    // TODO: Implement profile update API call
    setTimeout(() => {
      toast.success('Profile updated successfully');
      setIsSaving(false);
    }, 1000);
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Profile Information
        </h2>
        <p className="text-gray-600">
          Update your personal information and preferences
        </p>
      </div>

      <div className="space-y-6">
        {/* Basic Information */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <User size={18} />
            Basic Information
          </h3>

          <div className="space-y-4">
            {/* Avatar */}
            <div className="flex items-center gap-4">
              <div className="h-20 w-20 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-2xl font-bold">
                JD
              </div>
              <div>
                <Button variant="outline" size="sm">
                  Change Avatar
                </Button>
                <p className="text-xs text-gray-500 mt-1">JPG, PNG or GIF (max. 2MB)</p>
              </div>
            </div>

            {/* Full Name */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  placeholder="John"
                  defaultValue="John"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  placeholder="Doe"
                  defaultValue="Doe"
                />
              </div>
            </div>

            {/* Email */}
            <div className="space-y-2">
              <Label htmlFor="email" className="flex items-center gap-2">
                <Mail size={14} />
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="john.doe@example.com"
                defaultValue="john.doe@example.com"
                disabled
              />
              <p className="text-xs text-gray-500">
                Email cannot be changed. Contact support if you need to update it.
              </p>
            </div>

            {/* Job Title */}
            <div className="space-y-2">
              <Label htmlFor="jobTitle" className="flex items-center gap-2">
                <Briefcase size={14} />
                Job Title
              </Label>
              <Input
                id="jobTitle"
                placeholder="Data Analyst"
                defaultValue="Data Analyst"
              />
            </div>
          </div>
        </Card>

        {/* Preferences */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Globe size={18} />
            Regional Preferences
          </h3>

          <div className="space-y-4">
            {/* Timezone */}
            <div className="space-y-2">
              <Label htmlFor="timezone" className="flex items-center gap-2">
                <Clock size={14} />
                Timezone
              </Label>
              <select
                id="timezone"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                defaultValue="UTC"
              >
                <option value="UTC">UTC (Coordinated Universal Time)</option>
                <option value="America/New_York">Eastern Time (ET)</option>
                <option value="America/Los_Angeles">Pacific Time (PT)</option>
                <option value="Europe/London">London (GMT)</option>
                <option value="Europe/Amsterdam">Amsterdam (CET)</option>
                <option value="Asia/Tokyo">Tokyo (JST)</option>
              </select>
            </div>

            {/* Language */}
            <div className="space-y-2">
              <Label htmlFor="language">Language</Label>
              <select
                id="language"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                defaultValue="en"
              >
                <option value="en">English</option>
                <option value="nl">Nederlands</option>
                <option value="de">Deutsch</option>
                <option value="fr">Français</option>
                <option value="es">Español</option>
              </select>
            </div>
          </div>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={() => toast.info('Changes discarded')}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </div>
  );
}
