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

const ajustes = defineCollection({
  loader: glob({ pattern: '*/ajustes.yaml', base: './src/content' }),
  schema: z.object({
    estado: z.enum(['preapertura', 'abierto']),
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
    }),
    formulario: z.object({
      endpoint: opcional,
    }),
    fundadores: z.object({
      mostrar: z.boolean(),
      plazasTotales: z.number().int().positive(),
      plazasLibres: z.number().int().min(0),
    }),
    cursorPersonalizado: z.boolean().default(false),
    medicion: z.object({
      googleAnalyticsId: opcional,
      metaPixelId: opcional,
    }),
    seo: z.object({
      titulo: texto,
      descripcion: texto,
    }),
  }),
});

const boton = z.object({ preapertura: texto, abierto: texto });

const home = defineCollection({
  loader: glob({ pattern: '*/home.yaml', base: './src/content' }),
  schema: ({ image }) => {
    // Foto real opcional: si se añade, sustituye a la ilustración de ese bloque.
    const foto = z.object({ imagen: image(), alt: texto }).optional();
    return z.object({
      menu: z.array(z.object({ texto, ancla: texto })),
      botones: z.object({
        principal: boton,
        principalCorto: boton,
        secundario: texto,
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
            fases: z.array(z.object({ etiqueta: texto, horas: z.array(texto), texto })),
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
        foto,
      }),
      dudas: z.object({
        titulo: texto,
        items: z.array(z.object({ pregunta: texto, respuesta: texto })),
      }),
      precios: z.object({
        titulo: texto,
        subtitulo: texto,
        porSesion: texto,
        membresias: z.array(
          z.object({
            nombre: texto,
            precio: z.number(),
            precioSesion: texto,
            pilates: texto,
            recovery: texto,
            extra: opcional,
            destacada: z.boolean().default(false),
            etiqueta: opcional,
          }),
        ),
        fundadores: z.object({
          etiqueta: texto,
          titulo: texto,
          ventajas: z.array(texto),
          pack: z.object({ titulo: texto, texto }),
          plazas: texto,
        }),
      }),
      estudio: z.object({
        titulo: texto,
        espacios: z.array(z.object({ icono: texto, texto, tono: z.enum(['claro', 'medio', 'sol', 'tinta']), foto })),
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
        grupos: z.array(
          z.object({
            titulo: texto,
            preguntas: z.array(z.object({ pregunta: texto, respuesta: opcional })),
          }),
        ),
      }),
      cierre: z.object({ titulo: texto, texto }),
      pie: z.object({
        horarioTitulo: texto,
        horario: z.array(texto),
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
