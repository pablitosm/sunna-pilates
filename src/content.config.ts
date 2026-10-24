import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

/*
 * Todo el contenido editable de la web vive en src/content/<idioma>/.
 * Este archivo solo comprueba que los datos tengan la forma correcta:
 * si falta un campo o hay un error de escritura, `npm run build` avisa.
 */

const texto = z.string();
const opcional = z.string().optional().default('');

// Ajustes comunes a todos los idiomas: solo existe src/content/es/ajustes.yaml.
const ajustes = defineCollection({
  loader: glob({ pattern: '*/ajustes.yaml', base: './src/content' }),
  schema: z.object({
    estado: z.enum(['preapertura', 'abierto']),
    paleta: z.enum(['naranja', 'salvia', 'arena', 'oliva', 'cacao']).default('naranja'),
    // Qué horario se muestra: el de las primeras semanas o el ampliado.
    horario: z.enum(['inicial', 'ampliado']).default('inicial'),
    fechaApertura: opcional,
    direccion: z.object({
      calle: texto,
      codigoPostal: texto,
      ciudad: texto,
      provincia: texto,
      pais: z.string().default('ES'),
      comoLlegar: opcional,
    }),
    contacto: z.object({
      whatsapp: opcional,
      telefonoAyuda: opcional,
      email: opcional,
      instagram: opcional,
      googleBusiness: opcional,
    }),
    reservas: z.object({
      primeraSesionUrl: opcional,
      horariosUrl: opcional,
      membresiasUrl: opcional,
      appUrl: opcional,
      // Tiendas de la app de SUNNA. Vacías: las insignias salen como «Próximamente».
      appStoreUrl: opcional,
      googlePlayUrl: opcional,
    }),
    formulario: z.object({
      endpoint: opcional,
    }),
    fundadores: z.object({
      mostrar: z.boolean(),
      plazasTotales: z.number().int().positive(),
      plazasLibres: z.number().int().min(0),
    }),
    medicion: z.object({
      googleAnalyticsId: opcional,
      metaPixelId: opcional,
    }),
  }),
});

// fundador: texto mientras la web está abierta y quedan plazas de socio fundador.
const boton = z.object({ preapertura: texto, abierto: texto, fundador: opcional });

const home = defineCollection({
  loader: glob({ pattern: '*/home.yaml', base: './src/content' }),
  schema: ({ image }) => {
    // Foto real opcional: si se añade, sustituye a la ilustración de ese bloque.
    const foto = z.object({ imagen: image(), alt: texto }).optional();
    return z.object({
      // Título y descripción para Google y al compartir el enlace.
      seo: z.object({ titulo: texto, descripcion: texto }),
      // Textos pequeños de la interfaz (accesibilidad, pie, selector de idioma…).
      ui: z.object({
        idioma: texto,
        saltar: texto,
        irInicio: texto,
        navegacion: texto,
        abrirMenu: texto,
        menu: texto,
        paso: texto,
        // Abre la letra pequeña de la reserva en Cómo funciona.
        detallesReserva: opcional,
        porMes: texto,
        mapaTitulo: texto,
        pieEstudio: texto,
        pieContacto: texto,
        pieLegal: texto,
        // Mensaje con el que se abre WhatsApp desde el botón flotante, el menú y el pie.
        whatsappMensaje: opcional,
        pieEspacios: opcional,
      }),
      // Cada entrada lleva a una página propia (pagina) o a una sección de la portada (ancla).
      // Una entrada puede agrupar varias páginas en un desplegable (submenu).
      menu: z.array(
        z.object({
          texto,
          pagina: z.enum(['primera-sesion', 'precios', 'reformer', 'luz-roja', 'sauna']).optional(),
          ancla: opcional,
          submenu: z
            .array(
              z.object({
                texto,
                pagina: z.enum(['primera-sesion', 'precios', 'reformer', 'luz-roja', 'sauna']),
                // Una línea bajo el nombre, en el desplegable del escritorio.
                descripcion: opcional,
              }),
            )
            .optional(),
        }),
      ),
      botones: z.object({
        principal: boton,
        principalCorto: boton,
        secundario: texto,
        precios: opcional,
      }),
      enlaces: z.object({
        horarios: texto,
        membresias: texto,
        app: texto,
      }),
      portada: z.object({
        titular: texto,
        subtitulo: texto,
        abrimos: texto,
        foto,
      }),
      // Por qué SUNNA frente a otros estudios, junto al acceso a la app.
      porQue: z
        .object({
          titulo: texto,
          intro: texto,
          // ampliado: título y texto alternativos cuando ajustes.yaml → horario es "ampliado".
          razones: z.array(z.object({ titulo: texto, texto, ampliado: z.object({ titulo: texto, texto }).optional() })),
          app: z.object({
            titulo: texto,
            texto: opcional,
            pasos: z.array(texto),
            // Paso 2 mientras quedan plazas de socio fundador.
            pasoFundador: opcional,
            proximamente: texto,
            appStore: texto,
            googlePlay: texto,
          }),
        })
        .optional(),
      // Accesos rápidos a cada espacio y a los precios (portada).
      explora: z
        .object({
          titulo: texto,
          ver: texto,
          precios: z.object({ titulo: texto, texto }),
        })
        .optional(),
      // Página de la primera sesión gratis.
      primeraSesion: z
        .object({
          titulo: texto,
          texto,
          incluyeTitulo: texto,
          incluye: z.array(texto),
          reservarTitulo: texto,
          reservarTexto: opcional,
          web: texto,
          whatsapp: texto,
          whatsappMensaje: texto,
        })
        .optional(),
      queEs: z.object({
        titulo: texto,
        ideas: z.array(z.object({ icono: texto, titulo: texto, texto })),
      }),
      comoFunciona: z.object({
        titulo: texto,
        pasos: z.array(z.object({ icono: texto, titulo: texto, texto })),
        notaFinal: texto,
        datos: z.object({
          reserva: texto,
          cancelacion: texto,
          horario: z.object({
            titulo: texto,
            intro: opcional,
            // Una fase por horario; solo se muestra la que marca ajustes.yaml → horario.
            fases: z.array(
              z.object({
                fase: z.enum(['inicial', 'ampliado']),
                intro: opcional,
                etiqueta: opcional,
                horas: z.array(texto),
                texto,
              }),
            ),
            // Cómo se llena el día: franjas de más y menos demanda (tranquila = verde oliva).
            franjas: z
              .object({
                titulo: texto,
                items: z.array(z.object({ horas: texto, texto, tranquila: z.boolean().default(false) })),
              })
              .optional(),
          }),
        }),
      }),
      clases: z.object({
        titulo: texto,
        tipos: z.array(texto),
        tiposTitulo: texto,
        duraciones: z.array(z.object({ nombre: texto, minutos: texto })),
        idiomas: z.array(texto),
        idiomasTexto: texto,
        cascos: texto,
      }),
      recovery: z.object({
        etiqueta: texto,
        titulo: texto,
        lineas: z.array(texto),
        aviso: opcional,
        membresiaTitulo: texto,
        apartados: z.array(
          z.object({
            tipo: z.enum(['reformer', 'sauna', 'luz-roja']),
            titulo: texto,
            texto,
            puntos: z.array(texto),
            membresia: z.array(z.object({ plan: texto, cantidad: texto })),
            pendiente: opcional,
            foto,
          }),
        ),
      }),
      dudas: z.object({
        titulo: texto,
        items: z.array(z.object({ pregunta: texto, respuesta: texto })),
      }),
      precios: z.object({
        titulo: texto,
        subtitulo: opcional,
        // Texto bajo el título de precios.
        intro: opcional,
        introFundador: opcional,
        porSesion: texto,
        // Textos de los gráficos de cada tarjeta y del contacto bajo los precios.
        graficos: z
          .object({
            recovery: texto,
            luzRoja: texto,
            sauna: texto,
            ilimitado: texto,
            noIncluida: texto,
            // Unidad tras la cantidad de luz roja y sauna ("2 a la semana").
            porSemana: opcional,
          })
          .optional(),
        contacto: z.object({ titulo: texto, texto }).optional(),
        membresias: z.array(
          z.object({
            nombre: texto,
            precio: z.number(),
            precioSesion: texto,
            pilates: texto,
            // Equivalencia semanal, en pequeño bajo las sesiones al mes.
            pilatesSemana: opcional,
            recovery: texto,
            extra: opcional,
            destacada: z.boolean().default(false),
            // Para el recovery de la tarjeta. -1 = ilimitado.
            luzRoja: z.number().int().min(-1).optional(),
            sauna: z.number().int().min(-1).optional(),
            etiqueta: opcional,
          }),
        ),
        fundadores: z.object({
          etiqueta: texto,
          titulo: texto,
          ventajas: z.array(texto),
          pack: z.object({ titulo: texto, texto }),
          plazas: texto,
          verVentajas: texto,
        }),
      }),
      estudio: z.object({
        titulo: texto,
        espacios: z.array(z.object({ icono: texto, texto, tono: z.enum(['claro', 'medio', 'sol', 'tinta', 'rojo']), foto })),
        mapa: z.object({
          direccion: texto,
          comoLlegar: texto,
          boton: texto,
          aviso: texto,
          abrir: texto,
        }),
      }),
      faq: z.object({
        titulo: texto,
        // Cierre del FAQ: correo (ajustes.yaml → contacto.email) e Instagram.
        contacto: z.object({ titulo: texto, texto }).optional(),
        grupos: z.array(
          z.object({
            titulo: texto,
            // respuestaAmpliado sustituye a respuesta cuando ajustes.yaml → horario es "ampliado".
            preguntas: z.array(z.object({ pregunta: texto, respuesta: opcional, respuestaAmpliado: opcional })),
          }),
        ),
      }),
      // textoPreapertura sustituye a texto mientras la web está en preapertura.
      // fundador sustituye título y texto mientras quedan plazas de socio fundador (web abierta).
      cierre: z.object({
        titulo: texto,
        texto,
        textoPreapertura: opcional,
        fundador: z.object({ titulo: texto, texto }).optional(),
      }),
      pie: z.object({
        horarioTitulo: texto,
        // Líneas del horario en el pie, una lista por fase.
        horario: z.object({ inicial: z.array(texto), ampliado: z.array(texto) }),
        legal: z.array(z.object({ texto, url: texto })),
        cookies: texto,
      }),
      panel: z.object({
        preapertura: z.object({
          titulo: texto,
          texto,
          campos: z.object({ nombre: texto, email: texto, telefono: texto }),
          consentimiento: texto,
          privacidad: texto,
          enviar: texto,
          enviando: texto,
          exitoTitulo: texto,
          exitoTexto: texto,
          error: texto,
          sinConexion: texto,
          sinConexionSinContacto: texto,
          pie: texto,
        }),
        abierto: z.object({
          titulo: texto,
          texto,
          boton: texto,
          widget: opcional,
        }),
        whatsapp: texto,
        cerrar: texto,
      }),
      cookies: z.object({
        titulo: texto,
        texto,
        aceptar: texto,
        rechazar: texto,
        configurar: texto,
        guardar: texto,
        analitica: z.object({ titulo: texto, texto }),
        marketing: z.object({ titulo: texto, texto }),
      }),
    });
  },
});

const legal = defineCollection({
  loader: glob({ pattern: '*/legal/*.md', base: './src/content' }),
  schema: z.object({
    titulo: texto,
    descripcion: texto,
    actualizado: opcional,
  }),
});

export const collections = { ajustes, home, legal };
