import apiClient from './client'
import type { ForecastResponse, ModelInfoResponse, TrainResponse } from '@/types'

export const forecastApi = {
  get: () =>
    apiClient.get<ForecastResponse>('/forecast/').then((r) => r.data),

  train: () =>
    apiClient.post<TrainResponse>('/forecast/train').then((r) => r.data),

  modelInfo: () =>
    apiClient.get<ModelInfoResponse>('/forecast/model-info').then((r) => r.data),
}
