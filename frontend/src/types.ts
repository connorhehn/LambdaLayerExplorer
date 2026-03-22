export interface Package {
  name: string;
  version: string;
  summary: string;
  home_page: string;
  license: string;
  requires_python: string;
}

export interface Layer {
  name: string;
  arn: string;
  publisher: string;
  publisher_account: string;
  latest_version: number;
  latest_version_arn: string;
  compatible_runtimes: string[];
  compatible_architectures: string[];
  description: string;
  license: string;
  packages: Package[];
  package_count: number;
  layer_size_bytes: number;
  error?: string;
}

export interface LayersData {
  updated_at: string;
  layer_count: number;
  layers: Layer[];
}
