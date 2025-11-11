# 25-2_DSL_Modeling_MultiModal_WAVE
멀티모달 팀은 사용자가 이미지를 입력하면 이미지 속 객체들을 악기처럼 활용해 이미지의 상황과 무드에 맞게 기존 음악을 재구성하는 image-to-audio multimodal transformation WAVE를 구축하였습니다.

-----------
## PIPELINE
파이프라인은 크게 2단계로 구성됩니다. 
Phase 1: image-to-sound은 이미지로부터 sound_source를 생성합니다.
Phase 2: sound-to-music은 생성된 sound_source를 튜닝하여 음악으로 발전시킵니다. 
![Image](https://github.com/user-attachments/assets/96b6e40b-bab0-4838-981e-9cf323d4caf7)

![Image](https://github.com/user-attachments/assets/11477c4d-bd11-4c9e-80d4-8ddb27bf5330)
![Image](https://github.com/user-attachments/assets/842640bd-5f15-4c42-b604-a783b246a2af)
![Image](https://github.com/user-attachments/assets/254c5578-5363-42a3-a687-d3ef8bd383c1)

-----------
## Phase 1: Image-to-Sound
phase1에서 가장 중요한 목표는 이미지에 어울리는 효과음을 생성하는 것입니다.
이에 따라 먼저 text-to-audio 단계에서 어떤 사운드 생성 모델에 대해서 입력 형식을 어떻게 넣어줬을 때 효과음이 잘 생성되는지를 구체적으로 알아보고 이를 기준으로 삼은 뒤에 image-to-text를 구체화 하는 방식으로 진행했습니다. 
### 1-2. Text-to-Audio
task 목적에 따라 퀄리티 높은 사운드를 생성하는 모델을 실험을 통해 선정하였습니다. 최종 선정 모델은 AudioLDM2입니다.
![Image](https://github.com/user-attachments/assets/cebac3db-d377-4c39-9e35-5780c7a921a4)
![Image](https://github.com/user-attachments/assets/ff7baf4f-6ccc-4025-88e9-08b7f659bd9b)

![Image](https://github.com/user-attachments/assets/95496d2b-f0d4-466a-89eb-b233a3836258)
![Image](https://github.com/user-attachments/assets/aa28f653-0291-49d9-9060-d6b3de0e6f41)
### 1-1. Image-to-Text
본 단계에서는 AudioLDM2가 task 목적에 더 적합한 사운드를 생성하도록 image로부터 text로 구성된 source를 뽑아내는 VLM을 찾고 VLM의 프롬프트를 구체화하였습니다. 
![Image](https://github.com/user-attachments/assets/16f69069-0f55-442f-9abd-e9e0824e0792)
![Image](https://github.com/user-attachments/assets/8aba7fc9-0458-441e-8f4c-453d9d4d6602)
![Image](https://github.com/user-attachments/assets/bd78e3ee-3b12-4680-b496-4cf9aef82208)

![Image](https://github.com/user-attachments/assets/1b0d74b8-f070-44c0-ba59-9ae8c22ec9c5)
![Image](https://github.com/user-attachments/assets/fe50c5f0-2236-4161-87d4-72b209421e07)

![Image](https://github.com/user-attachments/assets/87fe233c-1e5a-4a7a-8f82-954ab170cbfc)

----------------
## Phase 2: Sound-to-Music
Phase 1에서 생성한 사운드 소스들을 각각 drum, guitar, bass, keyboard 중 하나로 수동 매핑하고 세션별로 soundfont를 추출한 후 악보의 음에 매핑하여 음악을 재구성합니다. 
![Image](https://github.com/user-attachments/assets/4be02bbe-cf62-43d5-9589-133f97a50850)
![Image](https://github.com/user-attachments/assets/56658b38-b909-4999-89da-3353901560c1)
![Image](https://github.com/user-attachments/assets/85fe5dd8-86e3-4cec-bbb6-dfc63f100d4a)
![Image](https://github.com/user-attachments/assets/c34a833b-0f3b-4c1f-aaa5-edbbc445a2ae)
![Image](https://github.com/user-attachments/assets/62040f34-2139-4ec2-af16-f4a8380c9f03)
![Image](https://github.com/user-attachments/assets/b16cd577-6463-42a7-a4e6-83b1ab8eefd0)
![Image](https://github.com/user-attachments/assets/eca4411e-a896-4484-a930-839a7b33984a)
![Image](https://github.com/user-attachments/assets/38f6ba3d-fac2-4693-9814-47af45b17d60)
![Image](https://github.com/user-attachments/assets/9d8d52ff-cd6d-4253-88d8-985b4c3f25cf)
![Image](https://github.com/user-attachments/assets/ff81a6e0-0cf3-4086-ad88-1cb71af84163)

----------------
## Limiation & Future Work
![Image](https://github.com/user-attachments/assets/ac1a3137-b933-4eb7-8cdb-35dc306283b4)
![Image](https://github.com/user-attachments/assets/ab8cc8fe-4e77-4c6a-b270-c16a1072ce76)
