<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  labels: { type: Array, default: () => [] },
  revenueData: { type: Array, default: () => [] },
  grossProfitData: { type: Array, default: () => [] }
})

const chartRef = ref(null)
let chart = null

function renderChart() {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['营业收入', '毛利'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: props.labels, axisLabel: { formatter: '{value}月' } },
    yAxis: { type: 'value' },
    series: [
      { name: '营业收入', type: 'bar', data: props.revenueData, itemStyle: { color: '#4361ee' } },
      { name: '毛利', type: 'bar', data: props.grossProfitData, itemStyle: { color: '#f72585' } }
    ]
  }, true)
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch([() => props.labels, () => props.revenueData, () => props.grossProfitData], renderChart)

onBeforeUnmount(() => {
  chart?.dispose()
})
</script>

<template>
  <div ref="chartRef" style="width:100%;height:350px;"></div>
</template>
