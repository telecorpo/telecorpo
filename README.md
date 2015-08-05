<p align="center">
  <img alt="Marca do Poéticas Tecnológcias" src="https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/marca_poeticas_bg_branco_cor_pequeno.jpg"/>
</p>

# Telecorpo

Este é produto de uma pesquisa em andamento iniciada pouco após o [EVD58](http://embodied.mx/) no [Grupo de Pesquisa Poéticas Tecnológicas](http://www.poeticatecnologica.ufba.br/site/), desenvolvido por [Pedro lacerda](http://lattes.cnpq.br/8338596525330907) sobre orientação da professora [Ivani Santana](http://ivanisantana.net/).

# Introdução

Telecorpo é mais uma ferramenta para transmissão de vídeo pela internet ou rede local. Se distingue pela boa tolerância à perda de pacotes, compatibilidade com programas artísticos, como [Pure Data](http://puredata.info/) e  [Max/MSP/Jitter](http://cycling74.com/products/max/) e por transmitir eventos multi-câmera ao vivo pelo [Youtube](https://www.youtube.com/). Pode ser entendida como uma mesa de corte onde cada ponto de exibição pode alternar entre câmeras espalhadas pela rede. Outras ferramentas para transmissão de vídeo são [LoLa](http://www.conservatorio.trieste.it/artistica/lola-project/lola-low-latency-audio-visual-streaming-system), [Open Broadcaster Software](https://obsproject.com), [Arthron](http://gtavcs.lavid.ufpb.br/downloads/), etc.

Exceto para o Youtube, Telecorpo é incapaz de transmitir áudio, para isto tente  [JackTrip](https://ccrma.stanford.edu/groups/soundwire/software/jacktrip/), [NetJack](http://netjack.sourceforge.net/), etc.

Algumas características da rede impactam na qualidade da transmissão,  observe-as:

característica da rede | impacto na transmissão | |
---------------------- | ---------- |----------- |
delay | atraso na transmissão | para levar um pacote de dado de uma cidade até a outra ele precisa percorrer uma distância e atravessar equipamentos de rede |
perda de pacotes | degradação da imagem | perdas superiores a 1% podem inviabilizar, tente aumentar a frequência de key-frames enviados para compensar as perdas facilitando a reconstrução da imagem no decodificador, vide `x264 --keyint` ou `x264enc key-int-max` |
jitter | pequeno atraso na transmissão | um cache/buffer aguarda por pacotes atrasados para evitar a reconstrução errônea da imagem, mas descarta os muito atrasados |

A potência dos computadores também impacta no atraso porque exige um trabalho de tempo constante codificar as imagens, imagine que se para cada segundo capturado pela câmera demorasse o dobro para codificar/comprimir antes de enviar os dados pela rede? -- demoraria 20 segundos para codificar 10 segundos de imagem. Já a decodificação e exibição são trabalhos menos custosos, impactando menos o delay.

Em 27 e 28 de Setembro de 2014 foi utilizado no espetáculo de dança telemática Personare, apresentado em simultâneo e ao vivo entre Brasil, Chile e Portugal. [Mais](http://www.fmh.utl.pt/pt/noticias/fmh-e-noticia/item/2203-espetaculo-de-danca-personare-embodied-in-varios-darmstadt-58-dias-27-e-28-de-setembro-de-2014-na-fmh) [informações](http://www.anillaculturalmac.cl/es/eventos/personare_embodied_in_varios_darmstadt58_danza_telematica) [aqui](http://www.cultura.ba.gov.br/2014/09/24/espetaculo-de-danca-telematico-personare/). A transmissão ao vivo pelo Youtube ocorreu [neste link](http://youtu.be/r64rytEinE0?t=1h4m31s) (sem áudio por motivos terceiros).

![ilustração](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/1.png)


# Requisitos e Instalação

Você precisará de

* internet acadêmica ou rede local
* sistema operacional baseado em Debian (testado no Mint 17 e Ubuntu 14.04)
* câmera USB/Webcam ou Firewire® DV
* firewall desabilitado entre os computadores participantes

Para instalar execute a seguinte linha num terminal de comandos:

    $ wget -q -O - https://raw.githubusercontent.com/pslacerda/telecorpo/master/install.sh | sudo bash

O programa estará disponível no Menu Iniciar, ou pelo comando `telecorpo`.


# Guia rápido de uso

Telecorpo é composto por alguns módulos diferentes:

módulo | descrição
--------- | -----------
producer | captura uma ou mais câmeras e as disponibiliza como fluxos RTSP
viewer | mesa de corte que alterna entre os fluxos disponibilizados
server | indexa os fluxos ativos

Estes módulos precisam ser inicializados numa ordem específica:

1. Em uma das máquinas execute o comando `telecorpo server`. Apenas uma instância do servidor é necessária.![server.png](https://bitbucket.org/repo/RnKegx/images/1808291682-server.png)
2. Nas máquinas com câmeras conectadas vá para *Menu iniciar > Telecorpo > Producer*, escolha uma ou mais câmeras disponíveis (dica: use Ctrl+Mouse), escreva o endereço de IP do servidor, aperte em *Registrate*.![producer.png](https://bitbucket.org/repo/RnKegx/images/2233534168-producer.png)
3. Nas máquinas com projetores conectados vá para *Menu iniciar > Telecorpo > Viewer*, escreva o endereço de IP do servidor, aperte em *Registrate*. Note que cada instância deste programa consome uma quantidade de banda. ![viewer.png](https://bitbucket.org/repo/RnKegx/images/3140953753-viewer.png)
4. **Atenção:** Sempre abra todos os *producers*, para então abrir todos os *viewers*. Em caso de falhas, feche todos os componentes (incluindo o *server*)e repita o processo.

# Transmissão pelo Youtube

Para transmitir ao vivo pelo Youtube precisa de alguns passos adicionais:

1. Crie um novo evento ao vivo [nesta página](https://www.youtube.com/my_live_events), configure as opções básicas e avançadas como preferir, aperte no botão azul. ![screen1.png](https://bitbucket.org/repo/RnKegx/images/1943562889-screen1.png)
2. Na página subsequente escolha uma bitrate (deve ser compatível com a taxa de upload de sua rede), escolha o encoder *Other encoder*, anote o nome do *Stream name*. ![screen1.png](https://bitbucket.org/repo/RnKegx/images/260715811-screen1.png)
3. Tenha certeza que seu servidor JACK está ativo e execute o comando `python3 -m tc.youtube -r 360p -t my_name.a1b2-c3d4-e5f6-g7h8 rtsp://10.0.0.1:13371/video0` ajustando os parâmetros adequadamente.
4. Vá para a página *Live Control Room*, inicie o preview, inicie o streaming.
5. Listo

# Recepção de vídeo por aplicativos externos


## via RTSP

Cada câmera é transmitida por um stream RTSP e disponibilizada por uma URL compatível com diversas aplicações multimídia como [VLC](http://www.videolan.org/), [PdGst](https://github.com/umlaeute/pdgst/), etc:

    $ cvlc rtsp://10.0.0.1:13371/smpte

No [Max/MSP/Jitter](http://cycling74.com/products/max/) você pode configurar o objeto `[jit.qt.movie]` com a mensagem `[read rtsp://10.0.0.1:13371/smpte(`.


## via v4l2loopback (para Linux)

Especificamente no Linux, poderá capturar o stream por uma webcam virtual; a maioria dos programas com suporte a webcams será compatível. Tenha certeza que possui os pacotes necessários:

    $ sudo modprobe v4l2loopback video_nr=11,12
    $ gst-launch-0.10 uridecodebin uri=rtsp://10.0.0.1:13371/smpte ! v4l2sink sync=false device=/dev/video11

ou

    $ gst-launch-1.0 uridecodebin uri=rtsp://10.0.0.1:13371/smpte ! v4l2sink sync=false device=/dev/video11

Na webcam virtual `/dev/video11` estará disponível o stream `rtsp://10.0.0.1:13371/smpte`. Assim poderá acessar o vídeo remoto no [GEM](http://en.flossmanuals.net/pure-data/ch047_introduction/), por exemplo.
