<p align="center">
  <img alt="Marca do Poéticas Tecnológcias" src="https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/marca_poeticas_bg_branco_cor_pequeno.jpg"/>
</p>

# TeleCorpo

Este é produto de uma pesquisa iniciada pouco após o [EVD58](http://embodied.mx/) no [Grupo de Pesquisa Poéticas Tecnológicas](http://www.poeticatecnologica.ufba.br/site/). Foi desenvolvido por [Pedro Lacerda](http://lattes.cnpq.br/8338596525330907), sob orientação da professora [Ivani Santana](http://ivanisantana.net/), para o _Personare_, espetáculo de dança telemática apresentado em simultâneo e ao vivo entre Brasil, Chile e Portugal em 27 e 28 de setembro de 2014. [Mais](http://www.fmh.utl.pt/pt/noticias/fmh-e-noticia/item/2203-espetaculo-de-danca-personare-embodied-in-varios-darmstadt-58-dias-27-e-28-de-setembro-de-2014-na-fmh), [informações](http://www.anillaculturalmac.cl/es/eventos/personare_embodied_in_varios_darmstadt58_danza_telematica), [aqui](http://www.cultura.ba.gov.br/2014/09/24/espetaculo-de-danca-telematico-personare/).

## Tabela de Conteúdos
* [Introdução](#introdução)
* [Requisitos e instalação](#requisitos-e-instalação)
* [Arquitetura e Implementação](#arquitetura-e-implementação)
* [Guia rápido de uso](#guia-rápido-de-uso)
* [Transmissão para o Youtube](#transmissão-pelo-youtube)
* [Recepção de vídeo por aplicativos externos](#recepção-de-vídeo-por-aplicativos-externos)


# Introdução

Telecorpo é mais uma ferramenta para transmissão de vídeo pela internet ou rede local. Distingue-se pela boa tolerância à perda de pacotes, compatibilidade com programas artísticos, como [Pure Data](http://puredata.info/) e  [Max/MSP/Jitter](http://cycling74.com/products/max/), e por transmitir eventos multicâmera ao vivo pelo [Youtube](https://www.youtube.com/). Pode ser entendida como uma mesa de corte de vídeo, na qual cada ponto de exibição pode alternar entre câmeras espalhadas pela rede. Outras ferramentas para transmissão de vídeo são: [Arthron](http://gtavcs.lavid.ufpb.br/downloads/), [LoLa](http://www.conservatorio.trieste.it/artistica/lola-project/lola-low-latency-audio-visual-streaming-system), [Open Broadcaster Software](https://obsproject.com), [Scenic](http://code.sat.qc.ca/redmine/projects/scenic/wiki), [Snowmix](http://snowmix.sourceforge.net/), [UltraGrid](http://www.ultragrid.cz/), etc. Exceto para o Youtube, Telecorpo é incapaz de transmitir áudio, para isto experimente  [JackTrip](https://ccrma.stanford.edu/groups/soundwire/software/jacktrip/), [NetJack](http://netjack.sourceforge.net/), etc.

Algumas características da rede impactam na qualidade da transmissão,  observe-as:

característica da rede | impacto na transmissão | |
---------------------- | ---------- |----------- |
_delay_ | atraso na transmissão | para levar um pacote de dados de uma cidade até a outra, ele precisa percorrer uma distância e atravessar equipamentos de rede |
perda de pacotes | degradação da imagem | perdas superiores a 1% podem inviabilizar a transmissão, tente aumentar a frequência de key-frames enviados para compensar as perdas facilitando a reconstrução da imagem no decodificador, vide [`x264 --keyint`](http://manpages.ubuntu.com/manpages/intrepid/man1/x264.1.html) ou [`x264enc key-int-max`](http://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-ugly-plugins/html/gst-plugins-ugly-plugins-x264enc.html) |
_jitter_ | pequeno atraso na transmissão | devido à natureza das redes de computadores, pacotes podem chegar fora de ordem, uns mais atrasados do que outros, portanto _cache/buffer_ aguarda por pacotes atrasados para evitar a reconstrução errônea da imagem, mas descarta os muito atrasados, que são considerados perdidos |

A potência dos computadores também impacta no atraso/delay, custa um tempo capturar, codificar, decodificar e exibir. Computadores mais potentes podem realizar estas tarefas mais rapidamente. Comprimir os quadros/frames (**cod**ificar) custa mais processamento do que descomprimí-los (**dec**odificar), e por isso exibir é mais "leve" do que capturar.

 A transmissão ao vivo pelo Youtube ocorreu [neste link](http://youtu.be/r64rytEinE0?t=1h4m31s) (sem áudio por motivos secundários).

![ilustração](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/1.png)

# Requisitos e Instalação

Você precisará de

* internet acadêmica ou rede local
* sistema operacional baseado em Linux (testado no Mint 17, Ubuntu 14.04, Debian 8.1)
* câmera USB/Webcam ou Firewire® DV
* firewall desabilitado entre os computadores participantes

Pacotes `.deb` são fornecidos para facilitar a instalação. Tanto do TeleCorpo, quanto da biblioteca [GstRtspServer](http://cgit.freedesktop.org/gstreamer/gst-rtsp-server/), requerida pelo TeleCorpo. Caso queira construí-los "na mão", execute o _script_ `./create-packages`, ainda mais grato seria modificá-lo para também gerar pacotes `.rpm`.

[**`telecorpo_0.92_all.deb`**](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/telecorpo_0.92_all.deb) | [**`libgstrtspserver-1.0_1.4.4_amd64.deb`**](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/libgstrtspserver-1.0_1.4.4_amd64.deb)
-------------------------- | --------------------------------------

Para instalá-los, entre com:

    $ dpkg -i libgstrtspserver-1.0_1.4.4_amd64.deb
    $ dpkg -i telecorpo_0.92_all.deb

, que então o programa estará disponível no Menu Iniciar e pelo comando `telecorpo`.

# Arquitetura e Implementação

O desenho arquitetural da versão atual (v0.92) do Telecorpo consiste em três módulos essenciais para o funcionamento do programa, e um quarto, utilizado na transmissão para o grande público fora dos palcos. O protocolo subjacente escolhido foi o [RTSP](https://tools.ietf.org/html/rfc2326), semelhante ao HTTP, mas que transmite conteúdo audiovisual ao invés de hipertexto. Entretanto a vantagem da escolha foi o fato do RTSP disponibilizar os conteúdos (fluxos) por uma URL, tornando a ferramenta mais familiar para usuários não-técnicos.

Os _frameworks_ multimídia escolhidos foram o [GStreamer 1.0](http://gstreamer.freedesktop.org/) e o [gst-rtsp-server](http://cgit.freedesktop.org/gstreamer/gst-rtsp-server/), ambos escritos na linguagem de programação C. Devido à morosidade em se desenvolver aplicativos nesta linguagem, Telecorpo foi desenvolvido em [Python 3](https://www.python.org/), utilizando tais _frameworks_ através de _bindings_ gerados automaticamente pelo _middleware_ [GObject Introspection](https://wiki.gnome.org/Projects/GObjectIntrospection).

módulo | descrição
------ | -----------
`tc.producer` | captura uma ou mais câmeras e as disponibiliza como fluxos RTSP
`tc.viewer`   | mesa de corte de vídeo que alterna entre os fluxos disponibilizados
`tc.server`   | gerencia os fluxos ativos
`tc.youtube`  | transmite video para o grande público

O programa poderia ser dito não-_macarrônico_ de acordo com o [Progamador Pragmático](http://www.saraiva.com.br/o-programador-pragmatico-3674493.html), pois mudanças num módulo não interfeririam em outro, já que não há dependências explícitas entre eles. Baixíssimo acoplamento, portanto. Mas há dependências em tempo de execução, que ocorrem na dinâmica do sistema, exigindo uma ordem específica para inicialização dos componentes.

Com o `server` em execução, o `producer` registra nele os fluxos produzidos (câmeras capturadas). Então o `server` passa a consultar periodicamente cada URL de fluxo para verificar se ainda está ativa, e desregistrá-la caso a consulta falhe. Já o `viewer` é mais simples, apenas inquere periodicamente o `server` pelas URLs de fluxos ainda ativos, isto é, não encerradas.

O diagrama abaixo-esquerda mostra um `producer` registrando três câmeras diferentes, e sequência temporal de troca de mensagens relativas à câmera nomeada `fw0` até a consulta falhar, quando então `fw0` será desregistrada do `server`, significando que ou o `producer` foi encerrado ou falhou.  No diagrama abaixo-direita vê-se um `viewer` inquerindo pelas URLs de um `server` que possui inicialmente um `producer` registrado com duas câmeras ativas, quando então um outro `producer` é adicionado com uma terceira câmera. Note que os dois diagramas se referem à sistemas diferentes.

![ilustração](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/diagram1.png)

Já o módulo `youtube`, utilizado para transmitir vídeos ao vivo para o [Youtube Live](http://youtube.com/live), é completamente independente dos demais módulos, podendo ser utilizado para transmitir conteúdo que não foi gerado pelo próprio TeleCorpo. É necessário ter o servidor [JACK Audio Connection Kit](http://jackaudio.org/) em execução, ferramenta popular nos nichos profissionais de áudio e artes.


# Guia rápido de uso

Apenas uma instância do `server` é necessária para o funcionamento do sistema. `producer`s e `viewer`s podem ser inicializados tantos quantos forem necessários. Se você tem duas câmeras em dois países diferentes, será necessário inicializar dois `producer`s, um em cada país. Similarmente, se você tem três projetores em três países diferentes, será necessário inicializar três `viewers`, um em cada país.

Além de ser necessário iniciar os módulos em uma ordem específica devido à própria natureza dos sitemas distribuídos, existem defeitos de implementação que reafirmam a necessidade de cuidados na inicialização do sistema. O módulo `server` é o primeiro à ser executado, já que `producer`s e `viewer`s registram-se nele. Então, teoricamente, tantos quantos necessários, `producer`s e `viewer`s poderiam ser inicializados em qualquer ordem, mas devido à discrepâncias entre a arquitetura e implementação, poderá ser necessário inicializar primeiro os `producer`s, para então os `viewers`.

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

    $ sudo modprobe v4l2loopback video_nr=11,12
    $ gst-launch-1.0 uridecodebin uri=rtsp://10.0.0.1:13371/smpte ! v4l2sink sync=false device=/dev/video11

Na webcam virtual `/dev/video11` estará disponível o stream `rtsp://10.0.0.1:13371/smpte`. Assim poderá acessar o vídeo remoto no [GEM](http://en.flossmanuals.net/pure-data/ch047_introduction/), por exemplo. Para desativar os dispositivos virtuais, pare o processo `gst-launch` e desabilite o v4l2loopback:

    $ sudo modprobe -r v4l2loopback
