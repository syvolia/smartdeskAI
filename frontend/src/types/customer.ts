export interface Customer {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  company: string | null;
  phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerListResponse {
  items: Customer[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}