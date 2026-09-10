// /api/wan22/metadata — kernel-metadata.json 다운로드

export default function handler(req, res) {
  const meta = {
    id: 'ipynboutputandcheckoutputwithfiles',
    title: 'Wan2.2-TI2V Video Generator (Daon Parameterized)',
    code_file: 'kaggle_wan22_t2v_param.ipynb',
    language: 'python',
    kernel_type: 'notebook',
    is_private: true,
    enable_gpu: true,
    enable_internet: true,
    docker_image: 'tensorflow/tensorflow:2.13.0-gpu',
    dataset_sources: [],
    kernel_sources: [],
    competition_sources: [],
    model_inputs: {
      model_instance_type: 'external',
      model_framework: 'PyTorch',
      model_hardware: 'GPU',
    },
  };
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Content-Disposition', 'attachment; filename="kernel-metadata.json"');
  res.status(200).send(JSON.stringify(meta, null, 2));
}
