import apiClient from '@/lib/api-client';

export interface Database {
  name: string;
  display_name: string;
  engine: string;
  description: string;
}

export interface DatabaseListResponse {
  databases: Database[];
  total_count: number;
}

class DatabaseService {
  /**
   * Fetch accessible databases for current user.
   *
   * This endpoint returns databases from MindsDB filtered by user permissions via OPA.
   * Only databases the user has "read" access to will be returned.
   *
   * @returns Promise resolving to array of accessible databases
   */
  async getAccessibleDatabases(): Promise<Database[]> {
    try {
      // Check if user is authenticated before making request
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
      if (!token) {
        console.warn('No access token found, skipping database fetch');
        return [];
      }

      const response = await apiClient.get<DatabaseListResponse>('/api/databases/');
      return response.data.databases || [];
    } catch (error: any) {
      console.error('Failed to fetch databases:', error);

      // Return empty array on error to allow UI to still function
      // User will see "No databases available" in dropdown
      return [];
    }
  }
}

export const databaseService = new DatabaseService();
