import pytest
import numpy as np
from PIL import Image
from unittest.mock import patch, MagicMock
from core.face_engine import FaceEngine

@pytest.fixture
def mock_mtcnn():
    with patch('core.face_engine.MTCNN') as mock:
        yield mock

@pytest.fixture
def mock_resnet():
    with patch('core.face_engine.InceptionResnetV1') as mock:
        yield mock

def test_no_face_detected(mock_mtcnn, mock_resnet):
    # Setup mock to return no faces
    mock_mtcnn_instance = MagicMock()
    mock_mtcnn_instance.return_value = (None, None)
    mock_mtcnn.return_value = mock_mtcnn_instance
    
    engine = FaceEngine()
    img = Image.new('RGB', (100, 100), color='black')
    
    with pytest.raises(ValueError, match="No face detected"):
        engine.process_face(img)

def test_multiple_faces_detected(mock_mtcnn, mock_resnet):
    # Setup mock to return multiple faces
    mock_mtcnn_instance = MagicMock()
    mock_mtcnn_instance.return_value = (["face1", "face2"], [0.99, 0.98])
    mock_mtcnn.return_value = mock_mtcnn_instance
    
    engine = FaceEngine()
    img = Image.new('RGB', (100, 100), color='black')
    
    with pytest.raises(ValueError, match="Multiple faces"):
        engine.process_face(img)

def test_single_face_success(mock_mtcnn, mock_resnet):
    # Setup MTCNN mock
    import torch
    mock_mtcnn_instance = MagicMock()
    # MTCNN returns a tensor of shape (1, 3, 160, 160) for one face if keep_all=True
    # faces list contains 1 face tensor
    mock_face_tensor = torch.zeros(3, 160, 160)
    mock_mtcnn_instance.return_value = ([mock_face_tensor], [0.99])
    mock_mtcnn.return_value = mock_mtcnn_instance
    
    # Setup Resnet mock
    mock_resnet_instance = MagicMock()
    mock_resnet.return_value = mock_resnet_instance
    mock_resnet_instance.eval.return_value = mock_resnet_instance
    mock_resnet_instance.to.return_value = mock_resnet_instance
    
    # Mock the return chain: resnet(face_tensor).squeeze(0).cpu().numpy()
    mock_tensor = MagicMock()
    mock_tensor.squeeze.return_value.cpu.return_value.numpy.return_value = np.zeros(512)
    mock_resnet_instance.return_value = mock_tensor
    
    engine = FaceEngine()
    img = Image.new('RGB', (100, 100), color='black')
    
    embedding = engine.process_face(img)
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (512,)
