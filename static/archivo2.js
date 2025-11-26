//MANEJO DE TRY CATCH
function dividir(a,b){
    try {
        if(b===0){
            throw new Error("no se puede dividir un entero");
        }
        return a/b;
    } catch (error) {
        console.error(error);
        return null;
    }
}
console.log(dividir(4,0));
//FUNCIONES ASINCRONICAS
//tiempo de espera
function getData(callback){
    setTimeout(()=>{
        const data={
            nombre:"xiaofen",edad:30
        };
        callback(data);
    },2000);
}
//funcion callback(mostrado)
function displayData(data){
    setTimeout(()=>{
        console.log(`Nombre:${data.nombre}, Edad:${data.edad}`);
    },1000);
}
getData(displayData);
//funciones asincronicas
//promesas: objetos q representan la respuesta a un proceso maneja 3 esatdos:
//prendiente
//cumplida
//rechazada
//es rigido
//existe otro tipo de objeto q es mas flexible son los observables
function esperar(milisegundos){
    return new Promise(resolve=>{
        setTimeout(()=>{
            resolve(`Espera termina en ${milisegundos}`);
        },milisegundos);
    });
}
//creando la funcion asincronica
async function proceso() {
    console.log("iniciando...")
    const resultado=await esperar(2000)
    console.log(resultado);
}
proceso()


//para q sirve una funcion asincronica: para un tiempo de espera