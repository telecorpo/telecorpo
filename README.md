<p align="center">
  <img alt="Marca do Poéticas Tecnológcias" src="https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/marca_poeticas_bg_branco_cor_pequeno.jpg"/>
</p>

# TeleCorpo

Este é produto de uma pesquisa iniciada pouco após o [EVD58](http://embodied.mx/) no [Grupo de Pesquisa Poéticas Tecnológicas](http://www.poeticatecnologica.ufba.br/site/). Foi desenvolvido por [Pedro Lacerda](http://lattes.cnpq.br/8338596525330907), sob orientação da professora [Ivani Santana](http://ivanisantana.net/), para o _Personare_, espetáculo de dança telemática apresentado em simultâneo e ao vivo entre Brasil, Chile e Portugal em 27 e 28 de setembro de 2014. [Mais](http://www.fmh.utl.pt/pt/noticias/fmh-e-noticia/item/2203-espetaculo-de-danca-personare-embodied-in-varios-darmstadt-58-dias-27-e-28-de-setembro-de-2014-na-fmh), [informações](http://www.anillaculturalmac.cl/es/eventos/personare_embodied_in_varios_darmstadt58_danza_telematica), [aqui](http://www.cultura.ba.gov.br/2014/09/24/espetaculo-de-danca-telematico-personare/).

## Tabela de Conteúdos
* [Requisitos e instalação](#requisitos-e-instalação)
* [Introdução](#introdução)
* [Transmissão de vídeo](#transmissão-de-vídeo)
* [Arquitetura e Implementação](#arquitetura-e-implementação)
* [Guia rápido de uso](#guia-rápido-de-uso)
* [Transmissão para o Youtube](#transmissão-pelo-youtube)
* [Recepção de vídeo por aplicativos externos](#recepção-de-vídeo-por-aplicativos-externos)
* [***Todo*** - *procura-se desenvolvedores*](#todo) 

# Requisitos e Instalação

Você precisará de

* Internet acadêmica ou rede local
* Sistema operacional baseado em Linux
  * Debian 9 (stretch) - TESTADO
  * Ubuntu 15.04 (vivide vervet) - NÃO TESTADO
* Câmera USB/Webcam ou Firewire® DV
* Firewall desabilitado entre os computadores participantes
  * exceto consumidor como `tc.viewer`,  VLC, gst-launch, etc

O pacote seguinte `.deb` é fornecido para facilitar a instalação em alguns casos. Caso queira construí-los "à mão", execute o _script_ `./create-packages`, ainda mais grato seria modificá-lo para também gerar pacotes `.rpm`.

[**`telecorpo_0.106_all.deb`**](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/telecorpo_0.106_all.deb)

Para instalá-lo, baixe o arquivo e execute a seguinte linha num terminal de comandos:

    $ dpkg -i telecorpo_0.106_all.deb
    $ apt-get -f install

Após a instalação o programa estará disponível no Menu Iniciar e pelo comando `telecorpo`. Alternativamente também é possível instalá-lo com a seguinte linha:

    $ wget -q -O - https://raw.githubusercontent.com/telecorpo/telecorpo/master/install.sh | sudo bash

    
# Introdução

Telecorpo é mais uma ferramenta para transmissão de vídeo pela internet ou rede local. Distingue-se pela boa tolerância à perda de pacotes, compatibilidade com programas artísticos, como [Pure Data](http://puredata.info/) e  [Max/MSP/Jitter](http://cycling74.com/products/max/), e por transmitir eventos multicâmera ao vivo pelo [Youtube](https://www.youtube.com/). Pode ser entendida como uma mesa de corte de vídeo, na qual cada ponto de exibição pode alternar entre câmeras espalhadas pela rede. É o produto de uma pesquisa iniciada pouco após o espetáculo [EVD58](http://embodied.mx/) no [Grupo de Pesquisa Poéticas Tecnológicas](http://www.poeticatecnologica.ufba.br/site/), e foi desenvolvido para o _Personare_, espetáculo de dança telemática apresentado em simultâneo e ao vivo entre Brasil, Chile e Portugal em 27 e 28 de setembro de 2014. A transmissão ao vivo pelo Youtube ocorreu [neste link](http://youtu.be/r64rytEinE0?t=1h4m31s) (sem áudio por motivos secundários).

Outras ferramentas para transmissão de vídeo são: [Arthron](http://gtavcs.lavid.ufpb.br/downloads/), [LoLa](http://www.conservatorio.trieste.it/artistica/lola-project/lola-low-latency-audio-visual-streaming-system), [Open Broadcaster Software](https://obsproject.com), [Scenic](http://code.sat.qc.ca/redmine/projects/scenic/wiki), [Snowmix](http://snowmix.sourceforge.net/), [UltraGrid](http://www.ultragrid.cz/), etc. Exceto para o Youtube, Telecorpo é incapaz de transmitir áudio, para isto experimente  [JackTrip](https://ccrma.stanford.edu/groups/soundwire/software/jacktrip/), [NetJack](http://netjack.sourceforge.net/), etc, ou outra das ferramentas anteriores.

# Transmissão de vídeo

Para transmitir vídeo através de uma rede de computadores, assim como qualquer outro tipo de informação, é necessário codificá-lo em _bits_. Esta transformação é feita por complexos algorítimos que, usualmente, além de **cod**ificar os dados, também comprime-os de modo a reduzir a quantidade de informação à ser trafegada. Por sua vez, o receptor utiliza um outro algorítimo complementar capaz de **dec**odificar e descomprimir os _bits_ em imagens.

A potência dos computadores impacta no atraso/_delay_ da transmissão porque custa um tempo capturar, codificar, decodificar e exibir. Computadores mais potentes podem realizar estas tarefas mais rapidamente. Comprimir os quadros/_frames_ (codificar) custa mais processamento do que descomprimí-los (decodificar), e por isso exibir é mais "leve" do que capturar.

A escolha do algorítimo codificador/decodificador (_codec_) e o conjunto de parâmetros que o configura influenciam fortemente tanto no atraso da transmissão (sendo mais ou menos eficientes), quanto na qualidade de imagem (comprimindo ao ponto de perder muitas informações), quanto na quantidade de informação à ser trafegada (maior ou menor capacidade de compressão).

Porém, em nossa observação, e desconsiderando a qualidade de implementação da ferramenta, são três características da rede as que mais influenciam na qualidade da transmissão. Observe-as na tabela abaixo:

característica da rede | impacto na transmissão | |
---------------------- | ---------- |----------- |
_delay_ | atraso na transmissão | para levar um pacote de dados de uma cidade até a outra, ele precisa percorrer uma distância e atravessar equipamentos de rede |
perda de pacotes | degradação da imagem | perdas superiores a 1% podem inviabilizar a transmissão |
_jitter_ | pequeno atraso na transmissão | devido à natureza das redes de computadores, pacotes podem chegar fora de ordem, uns mais atrasados do que outros, portanto _cache_/_buffer_ aguarda por pacotes atrasados para evitar a reconstrução errônea da imagem, mas descarta os muito atrasados, que são considerados perdidos |

A potência dos computadores também impacta no atraso/delay, custa um tempo capturar, codificar, decodificar e exibir. Computadores mais potentes podem realizar estas tarefas mais rapidamente. Comprimir os quadros/frames (**cod**ificar) custa mais processamento do que descomprimí-los (**dec**odificar), e por isso exibir é mais "leve" do que capturar.


![ilustração](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/1.png)

# Arquitetura e Implementação

O desenho arquitetural da versão atual (v0.92) do Telecorpo consiste em três módulos essenciais para o funcionamento do programa, e um quarto, utilizado na transmissão para o grande público fora dos palcos. O protocolo subjacente escolhido foi o [RTSP](https://tools.ietf.org/html/rfc2326), semelhante ao HTTP, mas que transmite conteúdo audiovisual ao invés de hipertexto. Entretanto a vantagem da escolha foi o fato do RTSP disponibilizar os conteúdos (fluxos) por uma URL, tornando a ferramenta mais familiar para usuários não-técnicos.

Os _frameworks_ multimídias escolhidos foram o [GStreamer 1.0](http://gstreamer.freedesktop.org/) e o [gst-rtsp-server](http://cgit.freedesktop.org/gstreamer/gst-rtsp-server/), ambos escritos na linguagem de programação C. Devido à morosidade em se desenvolver aplicativos nesta linguagem, Telecorpo foi desenvolvido em [Python 3](https://www.python.org/), utilizando tais _frameworks_ através de _bindings_ gerados automaticamente pelo _middleware_ [GObject Introspection](https://wiki.gnome.org/Projects/GObjectIntrospection).

módulo | descrição
------ | -----------
`tc.producer` | captura uma ou mais câmeras e as disponibiliza como fluxos RTSP
`tc.viewer`   | mesa de corte de vídeo que alterna entre os fluxos disponibilizados
`tc.server`   | gerencia os fluxos ativos
`tc.youtube`  | transmite video para o grande público

O programa poderia ser dito não-_macarrônico_ de acordo com o [Progamador Pragmático](http://www.saraiva.com.br/o-programador-pragmatico-3674493.html), pois mudanças num módulo não interfeririam em outro, já que não há dependências explícitas entre eles. Baixíssimo acoplamento, portanto. Mas há dependências em tempo de execução, que ocorrem na dinâmica do sistema, exigindo uma ordem específica para inicialização dos componentes.

Com o `server` em execução, o `producer` registra nele os fluxos produzidos (câmeras capturadas). Então o `server` passa a consultar periodicamente cada URL de fluxo para verificar se ainda está ativa, e desregistrá-la caso a consulta falhe. Já o `viewer` é mais simples, apenas inquere periodicamente o `server` pelas URLs de fluxos ainda ativos, isto é, não encerrados.

O diagrama abaixo-esquerda mostra um `producer` registrando três câmeras diferentes, e sequência temporal de troca de mensagens relativas a câmera nomeada `fw0` até a consulta falhar, quando então `fw0` será desregistrada do `server`, significando que ou o `producer` foi encerrado ou falhou.  No diagrama abaixo-direita vê-se um `viewer` inquerindo as URLs de um `server` que possui inicialmente um `producer` registrado com duas câmeras ativas, quando então um outro `producer` é adicionado com uma terceira câmera. Note que os dois diagramas se referem a sistemas diferentes.

![ilustração](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/diagram1.png)

Já o módulo `youtube`, utilizado para transmitir vídeos ao vivo para o [Youtube Live](http://youtube.com/live), é completamente independente dos demais módulos, podendo ser utilizado para transmitir conteúdo que não foi gerado pelo próprio TeleCorpo. É requerido ter o servidor [JACK Audio Connection Kit](http://jackaudio.org/) em execução, ferramenta popular nos nichos profissionais de áudio e artes.


# Guia rápido de uso

Basta apenas uma instância do `server` para o funcionamento do sistema. Os `producer`s e `viewer`s podem ser inicializados tantos quantos forem precisos. Se você tem duas câmeras em dois países diferentes, será necessário inicializar dois `producer`s, um em cada país. Similarmente, se você tem três projetores em três países diferentes, será necessário inicializar três `viewer`s, um em cada país.

Além de ser eixigada uma ordem específica para inicialização dos módulos devido à própria natureza dos sitemas distribuídos, existem defeitos de implementação que reafirmam a necessidade de cuidados na inicialização do sistema. O módulo `server` é sempre o primeiro à ser executado, já que `producer`s e `viewer`s se registram nele. Então, teoricamente, quantos forem demandados, `producer`s e `viewer`s poderiam ser inicializados em qualquer ordem, mas devido à discrepâncias entre a arquitetura e implementação, deverá inicializar primeiro os `producer`s, para depois os `viewer`s.

Veja abaixo a lista de etapas necessárias para utilização do TeleCorpo.

1. Em uma das máquinas execute o comando `telecorpo server`. Também anote endereço de IP desta máquina. necessária. ![server.png](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/server.png)
2. Nas máquinas com câmeras conectadas vá para *Menu iniciar > Telecorpo > Producer*, escolha uma ou mais câmeras disponíveis (use Ctrl+Mouse), escreva o endereço de IP do servidor, aperte em *Registrate*. ![producer.png](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/producer.png)
3. Nas máquinas com projetores conectados vá para *Menu iniciar > Telecorpo > Viewer*, escreva o endereço de IP do servidor, aperte em *Registrate*. Note que cada instância deste programa consome uma quantidade de banda. ![viewer1.png](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/viewer1.png)![viewer2.png](https://raw.githubusercontent.com/wiki/pslacerda/telecorpo/images/viewer2.png)

4. **Atenção:** Sempre abra todos os `producers`, para então abrir todos os `viewers`. Em caso de falhas, feche todos os componentes (incluindo o `server`) e repita o processo.

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

# Todo
Você pode ser o próximo desenvolvedor/mantenedor: Sinta-se livre para mandar emails, forks, mensagens, issues, etc!

 * Descobrir todas as portas usadas pela aplicação
 * Melhorar a interface Tkinter ou reescrever em Qt ou Gtk
  * Vários ajustes de design necessários!
  * expor na interface gráfica a variável `latency` do elemento `rtspsrc`
  * expor na interface gráfica a variável `speed-preset` do `x264enc`
 * Já pensou um canal UDP?
  * `tc.server` é descartado
  * `tc.producer`s enviam suas URLs a cada instante.
  * `tc.viewer`s recebem URLs periodicamente, quando param de receber o `tc.producer` foi encerrado.
 * Mais pacotes FPM:
  * RPM, BREW, etc
  * Git hooks para gerar pacotes DEB automaticamente
