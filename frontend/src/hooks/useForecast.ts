import { useQuery, useMutation } from '@tanstack/react-query'
import { forecastApi } from '@/api/forecast'
import toast from 'react-hot-toast'

export function useForecast() {
  return useQuery({
    queryKey: ['forecast'],
    queryFn: () => forecastApi.get(),
  })
}

export function useModelInfo() {
  return useQuery({
    queryKey: ['forecast', 'model-info'],
    queryFn: () => forecastApi.modelInfo(),
  })
}

export function useTrainModel() {
  return useMutation({
    mutationFn: () => forecastApi.train(),
    onSuccess: () => {
      toast.success('Model training started')
    },
  })
}
